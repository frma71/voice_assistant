#!/usr/bin/env python

# On chip you need to run
#   echo -1 > /sys/module/sun4i_codec/drivers/platform:sun4i-codec/1c22c00.codec/cdc/pmdown_time
# in order to keep the audio output hw awake, otherwise you will loose the first few words
#

from __future__ import print_function

from subprocess import call

import argparse
import os.path
import json
import re
import time

import google.oauth2.credentials

from google.assistant.library import Assistant
from google.assistant.library.event import EventType
from google.assistant.library.file_helpers import existing_file

import requests

import config

hass_pass = config.hass_pass
hass_ep = config.hass_ep

def play(fn):
        call(["play", "-qV0", fn])

def say(str):
        fn = "/tmp/" + str + ".wav"
        if not os.path.exists(fn):
                call(["pico2wave", "-w", fn, "<volume level='40'><pitch level='150'>" + str])
        call(["play", "-qV0", fn, "treble", "24"])

def hassrun(entity, service):
        url = hass_ep + "/services/" + service
        headers = {'x-ha-access': hass_pass, 'content-type': 'application/json'}
        data = '{"entity_id":"' + entity + '"}'
        response = requests.post(url, headers=headers,data=data)

def hassdim(entity, percent):
        url = hass_ep + "/services/light/turn_on"
        headers = {'x-ha-access': hass_pass, 'content-type': 'application/json'}
        data = '{"entity_id":"' + entity + '", "brightness_pct":"' + percent + '"}'
        response = requests.post(url, headers=headers,data=data)


def hass_state(entity):
        url = hass_ep + "/states/" + entity
        headers = {'x-ha-access': hass_pass, 'content-type': 'application/json'}
        response = requests.get(url, headers=headers)
        return response

def hass_location(device):
        r = hass_state("device_tracker." + device);
        return r.json()['state'].split(' - ')[-1]

lights = { "light.kitchenroof":
           [
                   re.compile(r'^(the )?kitchen( roof)?( light(s)?)?$'),
           ],
           "light.koksfonster":
           [
                   re.compile(r'^(the )?kitchen window( light(s)?)?$'),
           ],
           "light.livingroomroof":
           [
                   re.compile(r'^(the )?living room( roof)?( light(s)?)?$'),
           ],
           "light.vardagsrumsfonster":
           [
                   re.compile(r'^(the )?living room window( light(s)?)?$'),
           ],
           "light.hallwayroof":
           [
                   re.compile(r'^(the )?(hallway|entrance)( roof)?( light(s)?)?$'),
           ],
           "light.bedroom":
           [
                   re.compile(r'^(the )?bedroom( roof)?( light(s)?)?$'),
           ],
           "light.toa":
           [
                   re.compile(r'^(the )?(restroom|toilet)( roof)?( light(s)?)?$'),
           ],
           "switch.projector":
           [
                   re.compile(r'^(the )?(projector|tv)$'),
           ],
           "switch.amplifier":
           [
                   re.compile(r'^(the )?amplifier$'),
           ],
           "switch.livingroomshelf":
           [
                   re.compile(r'^(the )?(living room )?shelf( light(s)?)?$'),
           ],
           "group.window_lights":
           [
                   re.compile(r'^(the )?window light(s)?$'),
           ],
        }

def text_to_entity(name):
        print("Find:",name)
        for e in lights:
                for alias in lights[e]:
                        if re.compile(alias).match(name):
                                print("Found:",e)
                                return e
        print("Nothing found")
        return None

def process_local_cmd(event, assistant):
        """Process local commands

        Process local commands, not sent to google

        Args:
           event(event.Event): The event
        """
        text = event.args['text'].lower()
        print("Got:",text)
        if text.startswith('turn off'):
                assistant.stop_conversation()
                _,_,name = text.split(' ', 2)
                entity = text_to_entity(name);
                if not entity:
                        say("I dont't know how to turn off " + name);
                else:
                        print("Turn off: " + entity)
                        say("Will do")
                        hassrun(entity, "homeassistant/turn_off")
        elif text.startswith('turn on'):
                assistant.stop_conversation()
                (_,_,name) = text.split(' ', 2)
                entity = text_to_entity(name);
                if not entity:
                        say("I dont't know how to turn on " + name);
                else:
                        print("Turn on: " + entity)
                        say("Will do");
                        hassrun(entity, "homeassistant/turn_on")
        elif text.startswith('dim '):
                words=text.split(' ')
                if len(words) > 3 and words[-2] == 'to' and re.compile(r'^(100|([0-9][0-9]?))%$').match(words[-1]):
                        assistant.stop_conversation()
                        name = ' '.join(words[1:-2])
                        entity = text_to_entity(name);
                        if not entity:
                                say("I dont't know how to turn on " + name);
                        else:
                                print("do dim")
                                say("Ok, to " + words[-1])
                                hassdim(entity, words[-1][0:-1])
        elif text == "movie time":
                assistant.stop_conversation()
                say("Ok, lets hope it's good");
                hassrun("scene.movie", "scene/turn_on")
        elif text == "good night":
                assistant.stop_conversation()
                say("Ok, sleep tight");
                hassrun("scene.sleep", "scene/turn_on")
        elif text == "good morning":
                assistant.stop_conversation()
                say("Ok, welcome to another beautiful day");
                hassrun("scene.morning", "scene/turn_on")
        elif text == "where is asa":
                assistant.stop_conversation()
                say("Asa is at" + hass_location("asa_phone"))
        elif text == "where is frederick":
                assistant.stop_conversation()
                say("Fredrik is at" + hass_location("fredrik_phone"))
        elif text == "start roomba":
                assistant.stop_conversation()
                say("Will do");
                hassrun("script.roomba_clean", "homeassistant/turn_on")
        elif text == "stop roomba":
                assistant.stop_conversation()
                say("Will do");
                hassrun("script.roomba_stop", "homeassistant/turn_on")
        elif text == "park roomba":
                assistant.stop_conversation()
                say("Will do");
                hassrun("script.roomba_dock", "homeassistant/turn_on")
        else:
                return False

        return True

last_event = 0
def process_event(event, assistant):
    global last_event
    print(event)
    if event.type == EventType.ON_START_FINISHED:
        say("Welcome to the machine")
    if event.type == EventType.ON_CONVERSATION_TURN_STARTED:
        play("/home/voiceassistant/beep.wav")

    if event.type == EventType.ON_RECOGNIZING_SPEECH_FINISHED and event.args:
        process_local_cmd(event, assistant)

    if (event.type == EventType.ON_CONVERSATION_TURN_FINISHED and
            event.args and not event.args['with_follow_on_turn']):
        print()
    last_event = time.time();


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('--credentials', type=existing_file,
                        metavar='OAUTH2_CREDENTIALS_FILE',
                        default=os.path.join(
                            os.path.expanduser('~/.config'),
                            'google-oauthlib-tool',
                            'credentials.json'
                        ),
                        help='Path to store and read OAuth2 credentials')
    args = parser.parse_args()
    with open(args.credentials, 'r') as f:
        credentials = google.oauth2.credentials.Credentials(token=None,
                                                            **json.load(f))

    with Assistant(credentials) as assistant:
        for event in assistant.start():
            process_event(event, assistant)


if __name__ == '__main__':
    main()
