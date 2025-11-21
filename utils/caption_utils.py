#!/usr/bin/env python3
from data.lists import animal_list, list_food

def contains_animal(caption_text):
    caption_words = caption_text.lower().split()
    return any(mot in caption_words for mot in animal_list)

def contains_food(caption_text):
    caption_text = caption_text.lower()
    for mot_food in list_food:
        if mot_food in caption_text:
            return True
    return False