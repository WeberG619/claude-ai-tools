#!/usr/bin/env python3
"""
HeyGen API Integration - Generate realistic talking avatar videos
Professional video production with gender-matched voices
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load API key
load_dotenv(Path(__file__).parent / '.env')
API_KEY = os.getenv('HEYGEN_API_KEY')
BASE_URL = "https://api.heygen.com"

HEADERS = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

# Pre-defined professional avatars with matched voices
AVATARS = {
    # Male avatars
    "josh_business": {
        "id": "Josh_lite3_20230714",
        "gender": "male",
        "description": "Professional male in business attire"
    },
    "tyler_casual": {
        "id": "Tyler-incasualsuit-20220721",
        "gender": "male",
        "description": "Casual professional male"
    },
    "edward_suit": {
        "id": "Edward_public_pro2_20230608",
        "gender": "male",
        "description": "Male in formal suit"
    },
    # Female avatars
    "adriana_business": {
        "id": "Adriana_Business_Front_public",
        "gender": "female",
        "description": "Professional female in business attire"
    },
    "monica_office": {
        "id": "Monica_public_2_20240110",
        "gender": "female",
        "description": "Professional female in office setting"
    },
    "anna_presenter": {
        "id": "Anna_public_3_20240108",
        "gender": "female",
        "description": "Female presenter style"
    }
}

# Pre-defined professional voices
VOICES = {
    # Male voices (natural, professional)
    "male_professional": "2eca0d3dd5ec4a1ea6efa6194b19eb78",  # Ray
    "male_friendly": "a50b2b18a4bf49109caf46a3a6c6a08a",     # Marco
    "male_authoritative": "3ae75279043648ce8f96310333c9288f", # Mike
    # Female voices (natural, professional)
    "female_professional": "1985fa8325934283b196874ee42c1e48", # Sara
    "female_friendly": "f5d43dbe45b54852a18c8e2c93297c60",    # Emily
    "female_warm": "b60379bc29ae4b7c9bbd17e7cb250f4a"         # Jessica
}

def get_quota():
    """Check remaining credits"""
    resp = requests.get(f"{BASE_URL}/v2/user/remaining_quota", headers=HEADERS)
    data = resp.json()
    if data.get('error'):
        print(f"Error: {data['error']}")
        return None
    return data['data']

def list_avatars():
    """List available avatars"""
    resp = requests.get(f"{BASE_URL}/v2/avatars", headers=HEADERS)
    data = resp.json()
    if data.get('error'):
        print(f"Error: {data['error']}")
        return []
    return data.get('data', {}).get('avatars', [])

def list_voices():
    """List available voices"""
    resp = requests.get(f"{BASE_URL}/v2/voices", headers=HEADERS)
    data = resp.json()
    if data.get('error'):
        print(f"Error: {data['error']}")
        return []
    return data.get('data', {}).get('voices', [])

def get_gender_matched_voice(avatar_id, voice_style="professional"):
    """Get a voice that matches the avatar's gender"""
    # Check if it's a preset avatar
    for name, info in AVATARS.items():
        if info['id'] == avatar_id:
            gender = info['gender']
            voice_key = f"{gender}_{voice_style}"
            return VOICES.get(voice_key, VOICES[f"{gender}_professional"])

    # Try to detect gender from avatar name
    avatar_lower = avatar_id.lower()
    female_names = ['adriana', 'anna', 'monica', 'angela', 'sarah', 'lisa', 'emma', 'kate', 'sophia', 'emily', 'jessica', 'maria']
    male_names = ['josh', 'tyler', 'edward', 'mike', 'john', 'david', 'james', 'robert', 'michael', 'william', 'daniel', 'aditya', 'adrian', 'marco', 'ray']

    for name in female_names:
        if name in avatar_lower:
            return VOICES.get(f"female_{voice_style}", VOICES["female_professional"])

    for name in male_names:
        if name in avatar_lower:
            return VOICES.get(f"male_{voice_style}", VOICES["male_professional"])

    # Default to male professional
    return VOICES["male_professional"]

def create_video_from_text(text, avatar_id=None, voice_id=None, output_path=None,
                           gender=None, voice_style="professional", resolution="720p"):
    """
    Generate a talking avatar video from text with gender-matched voice

    Args:
        text: The script for the avatar to speak
        avatar_id: HeyGen avatar ID (uses default if None)
        voice_id: Voice ID (auto-matched to gender if None)
        output_path: Where to save the video (optional)
        gender: 'male' or 'female' - picks appropriate default avatar
        voice_style: 'professional', 'friendly', or 'warm'
        resolution: '720p' or '1080p'
    """
    # Select avatar based on gender if not specified
    if not avatar_id:
        if gender == "male":
            avatar_id = AVATARS["josh_business"]["id"]
        else:
            avatar_id = AVATARS["adriana_business"]["id"]

    # Auto-match voice to avatar gender if not specified
    if not voice_id:
        voice_id = get_gender_matched_voice(avatar_id, voice_style)

    # Set resolution
    if resolution == "1080p":
        width, height = 1920, 1080
    else:
        width, height = 1280, 720

    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "input_text": text,
                "voice_id": voice_id
            }
        }],
        "dimension": {
            "width": width,
            "height": height
        }
    }

    print(f"Creating video with avatar: {avatar_id}")
    print(f"Voice ID: {voice_id}")
    resp = requests.post(f"{BASE_URL}/v2/video/generate", headers=HEADERS, json=payload)
    data = resp.json()

    if data.get('error'):
        print(f"Error: {data['error']}")
        return None

    video_id = data['data']['video_id']
    print(f"Video ID: {video_id}")

    # Poll for completion
    return wait_for_video(video_id, output_path)

def create_video_from_audio(audio_path, avatar_id=None, output_path=None, gender=None):
    """
    Generate a talking avatar video from an audio file
    """
    print("Uploading audio...")

    with open(audio_path, 'rb') as f:
        files = {'file': f}
        upload_headers = {"X-Api-Key": API_KEY}
        resp = requests.post(f"{BASE_URL}/v2/asset", headers=upload_headers, files=files)

    data = resp.json()
    if data.get('error'):
        print(f"Upload error: {data['error']}")
        return None

    audio_asset_id = data['data']['asset_id']
    print(f"Audio uploaded: {audio_asset_id}")

    if not avatar_id:
        if gender == "male":
            avatar_id = AVATARS["josh_business"]["id"]
        else:
            avatar_id = AVATARS["adriana_business"]["id"]

    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "audio",
                "audio_asset_id": audio_asset_id
            }
        }],
        "dimension": {
            "width": 1280,
            "height": 720
        }
    }

    print("Creating video...")
    resp = requests.post(f"{BASE_URL}/v2/video/generate", headers=HEADERS, json=payload)
    data = resp.json()

    if data.get('error'):
        print(f"Error: {data['error']}")
        return None

    video_id = data['data']['video_id']
    print(f"Video ID: {video_id}")

    return wait_for_video(video_id, output_path)

def wait_for_video(video_id, output_path=None):
    """Poll until video is ready, then download"""
    print("Processing video", end="", flush=True)

    while True:
        resp = requests.get(f"{BASE_URL}/v1/video_status.get?video_id={video_id}", headers=HEADERS)
        data = resp.json()

        status = data['data']['status']

        if status == 'completed':
            print(" Done!")
            video_url = data['data']['video_url']
            print(f"Video URL: {video_url}")

            if output_path:
                print(f"Downloading to {output_path}...")
                video_resp = requests.get(video_url)
                with open(output_path, 'wb') as f:
                    f.write(video_resp.content)
                print(f"Saved to: {output_path}")

            return video_url

        elif status == 'failed':
            print(" Failed!")
            print(f"Error: {data['data'].get('error', 'Unknown error')}")
            return None

        print(".", end="", flush=True)
        time.sleep(5)

def create_multi_scene_video(scenes, output_path=None):
    """
    Create a video with multiple scenes/segments

    Args:
        scenes: List of dicts with 'text', 'avatar_id' (optional), 'voice_id' (optional)
        output_path: Where to save the final video
    """
    video_inputs = []

    for i, scene in enumerate(scenes):
        avatar_id = scene.get('avatar_id', AVATARS["adriana_business"]["id"])
        voice_id = scene.get('voice_id') or get_gender_matched_voice(avatar_id)

        video_inputs.append({
            "character": {
                "type": "avatar",
                "avatar_id": avatar_id,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "input_text": scene['text'],
                "voice_id": voice_id
            }
        })
        print(f"Scene {i+1}: {len(scene['text'])} chars")

    payload = {
        "video_inputs": video_inputs,
        "dimension": {
            "width": 1920,
            "height": 1080
        }
    }

    print(f"\nCreating {len(scenes)}-scene video...")
    resp = requests.post(f"{BASE_URL}/v2/video/generate", headers=HEADERS, json=payload)
    data = resp.json()

    if data.get('error'):
        print(f"Error: {data['error']}")
        return None

    video_id = data['data']['video_id']
    print(f"Video ID: {video_id}")

    return wait_for_video(video_id, output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate HeyGen talking avatar videos")
    parser.add_argument("--quota", action="store_true", help="Check remaining credits")
    parser.add_argument("--avatars", action="store_true", help="List available avatars")
    parser.add_argument("--voices", action="store_true", help="List available voices")
    parser.add_argument("--presets", action="store_true", help="Show preset avatars and voices")
    parser.add_argument("--text", type=str, help="Text for avatar to speak")
    parser.add_argument("--audio", type=str, help="Audio file path for lip-sync")
    parser.add_argument("--avatar", type=str, help="Avatar ID to use")
    parser.add_argument("--voice", type=str, help="Voice ID to use")
    parser.add_argument("--gender", type=str, choices=['male', 'female'], help="Avatar gender")
    parser.add_argument("--style", type=str, default="professional",
                       choices=['professional', 'friendly', 'warm'], help="Voice style")
    parser.add_argument("--resolution", type=str, default="1080p",
                       choices=['720p', '1080p'], help="Video resolution")
    parser.add_argument("--output", "-o", type=str, help="Output video path")

    args = parser.parse_args()

    if args.quota:
        quota = get_quota()
        if quota:
            print(f"Remaining credits: {quota['remaining_quota']}")
            print(f"Details: {json.dumps(quota['details'], indent=2)}")

    elif args.presets:
        print("=== Preset Avatars ===")
        for name, info in AVATARS.items():
            print(f"  {name}: {info['description']} ({info['gender']})")
        print("\n=== Preset Voices ===")
        for name, vid in VOICES.items():
            print(f"  {name}: {vid}")

    elif args.avatars:
        avatars = list_avatars()
        print(f"Found {len(avatars)} avatars:\n")
        for av in avatars[:30]:
            print(f"  {av['avatar_id']}: {av.get('avatar_name', 'N/A')}")

    elif args.voices:
        voices = list_voices()
        print(f"Found {len(voices)} voices:\n")
        en_voices = [v for v in voices if v.get('language', '').startswith('en')]
        for v in en_voices[:30]:
            print(f"  {v['voice_id']}: {v.get('display_name', v.get('name', 'N/A'))}")

    elif args.text:
        output = args.output or "heygen_output.mp4"
        create_video_from_text(
            args.text,
            args.avatar,
            args.voice,
            output,
            gender=args.gender,
            voice_style=args.style,
            resolution=args.resolution
        )

    elif args.audio:
        output = args.output or "heygen_output.mp4"
        create_video_from_audio(args.audio, args.avatar, output, gender=args.gender)

    else:
        parser.print_help()
