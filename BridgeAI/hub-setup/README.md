# BridgeAI Smart Hub Setup Guide

## What You Need
- Old Windows computer (Windows 10/11)
- Connected to your Starlink network
- About 15 minutes

## What This Does
Turns your old computer into a 24/7 smart home hub that you can control from anywhere in the world using your phone.

---

## STEP 1: Install Tailscale (5 minutes)

Tailscale creates a secure private network between your devices.

1. Go to: https://tailscale.com/download
2. Click "Download for Windows"
3. Install it
4. Sign in with Google, Microsoft, or GitHub account
5. Done! Your hub PC is now on your private network

## STEP 2: Copy BridgeAI to Hub PC

Copy this entire folder to the hub computer:
```
D:\_CLAUDE-TOOLS\BridgeAI\
```

## STEP 3: Run the Hub Setup Script

On the hub computer, run:
```
PowerShell -ExecutionPolicy Bypass -File "D:\_CLAUDE-TOOLS\BridgeAI\hub-setup\install-hub.ps1"
```

## STEP 4: Install Tailscale on Your Phone

1. Download "Tailscale" from App Store or Google Play
2. Sign in with the SAME account you used on the PC
3. Your phone can now reach the hub from anywhere!

## STEP 5: Test It

From your phone (even on mobile data):
1. Open browser
2. Go to: http://bridgeai-hub:5000 (or the Tailscale IP)
3. You should see the BridgeAI control panel

---

## What You Can Control

- Samsung TV (192.168.1.150)
- LG TV (192.168.1.46)
- More devices as you add them

## Commands Available

From anywhere, you can:
- Turn TVs on/off
- Change volume
- Check what's playing
- Open apps
- And more!
