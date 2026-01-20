#!/usr/bin/env python3
"""Quick test of Replicate pipeline with existing image."""

import os
import base64
import httpx
import time

REPLICATE_API_TOKEN = "r8_HtU11reGPKdxthkdfo8myHuHbwiWLQ92gZbcj"

# Read image
print("Reading captured image...")
with open('D:/temp/ai_renders/revit_capture.png', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

data_uri = f'data:image/png;base64,{image_data}'

prompt = "professional aerial architectural photography, bird's eye view site plan with lush landscaping, pool, driveway, surrounding context, photorealistic rendering, clear sunny day"
negative = "sketch, drawing, cartoon, blurry, low quality"

model_version = "lucataco/realistic-vision-v5.1:2c8e954decbf70b7607a4414e5785ef9e4de4b8c51d50fb8b8b349160e0ef6bb"

input_params = {
    'prompt': prompt,
    'image': data_uri,
    'prompt_strength': 0.55,
    'negative_prompt': negative,
    'guidance_scale': 7.5,
    'num_inference_steps': 30
}

headers = {
    'Authorization': f'Token {REPLICATE_API_TOKEN}',
    'Content-Type': 'application/json'
}

print('Sending to Replicate...')
with httpx.Client(timeout=120.0) as client:
    response = client.post(
        'https://api.replicate.com/v1/predictions',
        headers=headers,
        json={
            'version': model_version.split(':')[-1],
            'input': input_params
        }
    )

    if response.status_code != 201:
        print(f'Error: {response.status_code} - {response.text}')
        exit(1)

    prediction = response.json()
    prediction_url = prediction['urls']['get']
    print(f'Job started: {prediction["id"]}')

    # Poll
    for i in range(120):
        time.sleep(2)
        print('.', end='', flush=True)
        status_response = client.get(prediction_url, headers=headers)
        status_data = status_response.json()
        status = status_data.get('status')

        if status == 'succeeded':
            print(' Done!')
            output = status_data.get('output')
            if isinstance(output, list):
                output_url = output[0]
            else:
                output_url = output

            # Download
            img_response = client.get(output_url)
            output_path = 'D:/temp/ai_renders/render_test.png'
            with open(output_path, 'wb') as f:
                f.write(img_response.content)
            print(f'Saved to: {output_path}')
            break
        elif status == 'failed':
            print(f' Failed: {status_data.get("error")}')
            break
        elif status == 'canceled':
            print(' Canceled')
            break
