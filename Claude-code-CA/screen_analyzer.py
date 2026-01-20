#!/usr/bin/env python3
"""
Screen Analyzer Module - Computer Vision for UI Automation
Uses AI to understand what's on screen and find elements
"""

import os
import sys
import cv2
import numpy as np
import pytesseract
from PIL import Image, ImageGrab
import base64
import json
import asyncio
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class UIElement:
    """Represents a UI element found on screen"""
    type: str  # button, dialog, text, icon, etc.
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    center: Tuple[int, int]
    attributes: Dict[str, Any]

class ScreenAnalyzer:
    """Analyzes screenshots to find UI elements and understand screen state"""
    
    def __init__(self):
        self.last_screenshot = None
        self.element_cache = {}
        self.templates = self._load_templates()
        
        # Initialize Tesseract if available
        try:
            pytesseract.get_tesseract_version()
            self.ocr_available = True
        except:
            logger.warning("Tesseract not available - OCR features disabled")
            self.ocr_available = False
    
    def _load_templates(self) -> Dict[str, np.ndarray]:
        """Load template images for common UI elements"""
        templates = {}
        template_dir = "ui_templates"
        
        if os.path.exists(template_dir):
            for file in os.listdir(template_dir):
                if file.endswith(('.png', '.jpg')):
                    name = os.path.splitext(file)[0]
                    img = cv2.imread(os.path.join(template_dir, file))
                    templates[name] = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        return templates
    
    async def capture(self, reason: str = "analysis", region: Optional[Tuple[int, int, int, int]] = None) -> str:
        """Capture a screenshot"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"screenshot_{reason}_{timestamp}.png"
        
        try:
            if region:
                # Capture specific region
                screenshot = ImageGrab.grab(bbox=region)
            else:
                # Capture full screen
                screenshot = ImageGrab.grab()
            
            screenshot.save(filename)
            self.last_screenshot = filename
            
            logger.info(f"Screenshot captured: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            # Fallback to PowerShell method
            return await self._capture_with_powershell(filename)
    
    async def _capture_with_powershell(self, filename: str) -> str:
        """Fallback screenshot method using PowerShell"""
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms
        Add-Type -AssemblyName System.Drawing
        
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bitmap.Save('{filename}')
        $graphics.Dispose()
        $bitmap.Dispose()
        """
        
        import subprocess
        subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
        return filename
    
    async def analyze_screen(self, screenshot_path: Optional[str] = None) -> Dict[str, Any]:
        """Analyze the screen and identify UI elements"""
        if not screenshot_path:
            screenshot_path = self.last_screenshot
        
        if not screenshot_path or not os.path.exists(screenshot_path):
            raise ValueError("No screenshot available for analysis")
        
        # Load image
        image = cv2.imread(screenshot_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        analysis = {
            'screenshot': screenshot_path,
            'timestamp': datetime.now().isoformat(),
            'elements': [],
            'text_regions': [],
            'dialogs': [],
            'buttons': [],
            'state': {}
        }
        
        # Find dialogs
        dialogs = await self._find_dialogs(image, gray)
        analysis['dialogs'] = dialogs
        
        # Find buttons
        buttons = await self._find_buttons(image, gray)
        analysis['buttons'] = buttons
        
        # Extract text if OCR available
        if self.ocr_available:
            text_regions = await self._extract_text(gray)
            analysis['text_regions'] = text_regions
        
        # Detect application state
        analysis['state'] = await self._detect_application_state(image, analysis)
        
        # Combine all elements
        analysis['elements'] = dialogs + buttons + text_regions
        
        return analysis
    
    async def _find_dialogs(self, image: np.ndarray, gray: np.ndarray) -> List[UIElement]:
        """Find dialog boxes on screen"""
        dialogs = []
        
        # Method 1: Edge detection for rectangular regions
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Look for rectangular shapes
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                
                # Filter by size - dialogs are usually medium to large
                if w > 200 and h > 100 and w < image.shape[1] * 0.8:
                    # Check if it has typical dialog characteristics
                    roi = gray[y:y+h, x:x+w]
                    
                    # Look for title bar pattern (usually darker at top)
                    top_region = roi[:30, :]
                    if top_region.size > 0:
                        top_mean = np.mean(top_region)
                        body_mean = np.mean(roi[30:, :]) if roi[30:, :].size > 0 else top_mean
                        
                        if top_mean < body_mean - 20:  # Title bar is darker
                            dialog = UIElement(
                                type='dialog',
                                text='Dialog Window',
                                confidence=0.8,
                                bbox=(x, y, w, h),
                                center=(x + w//2, y + h//2),
                                attributes={'has_titlebar': True}
                            )
                            dialogs.append(dialog)
        
        # Method 2: Template matching for known dialog patterns
        if 'dialog_close_button' in self.templates:
            result = cv2.matchTemplate(gray, self.templates['dialog_close_button'], cv2.TM_CCOEFF_NORMED)
            threshold = 0.8
            locations = np.where(result >= threshold)
            
            for pt in zip(*locations[::-1]):
                # Found a close button, likely part of a dialog
                dialog = UIElement(
                    type='dialog',
                    text='Dialog with close button',
                    confidence=float(result[pt[1], pt[0]]),
                    bbox=(pt[0]-100, pt[1]-30, 300, 200),  # Estimate dialog size
                    center=(pt[0], pt[1]),
                    attributes={'close_button_location': pt}
                )
                dialogs.append(dialog)
        
        return dialogs
    
    async def _find_buttons(self, image: np.ndarray, gray: np.ndarray) -> List[UIElement]:
        """Find buttons on screen"""
        buttons = []
        
        # Method 1: Contour detection for button-like shapes
        # Apply threshold to get binary image
        _, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Button-like dimensions
            if 30 < w < 300 and 20 < h < 80 and 0.2 < h/w < 0.8:
                roi = gray[y:y+h, x:x+w]
                
                # Check if it has button-like appearance (relatively uniform)
                if roi.size > 0 and np.std(roi) < 50:
                    button_text = ""
                    if self.ocr_available:
                        text = pytesseract.image_to_string(roi, config='--psm 8').strip()
                        button_text = text
                    
                    button = UIElement(
                        type='button',
                        text=button_text,
                        confidence=0.7,
                        bbox=(x, y, w, h),
                        center=(x + w//2, y + h//2),
                        attributes={'style': 'standard'}
                    )
                    buttons.append(button)
        
        # Method 2: Look for X buttons (close buttons)
        # Common close button coordinates
        close_button_regions = [
            (1271, 497, 30, 30),  # Known Copilot position
            (1890, 10, 40, 40),   # Top-right corner
        ]
        
        for x, y, w, h in close_button_regions:
            if x < image.shape[1] and y < image.shape[0]:
                roi = gray[max(0,y-10):min(image.shape[0],y+h+10), 
                          max(0,x-10):min(image.shape[1],x+w+10)]
                
                if roi.size > 0:
                    # Check for X pattern or high contrast
                    if np.std(roi) > 30:  # Has variation (not uniform)
                        button = UIElement(
                            type='button',
                            text='X',
                            confidence=0.9,
                            bbox=(x, y, w, h),
                            center=(x + w//2, y + h//2),
                            attributes={'style': 'close', 'priority': 'high'}
                        )
                        buttons.append(button)
        
        return buttons
    
    async def _extract_text(self, gray: np.ndarray) -> List[UIElement]:
        """Extract text regions using OCR"""
        text_regions = []
        
        try:
            # Get detailed OCR data
            data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)
            
            n_boxes = len(data['text'])
            for i in range(n_boxes):
                if int(data['conf'][i]) > 60 and data['text'][i].strip():
                    x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                    
                    text_element = UIElement(
                        type='text',
                        text=data['text'][i],
                        confidence=data['conf'][i] / 100.0,
                        bbox=(x, y, w, h),
                        center=(x + w//2, y + h//2),
                        attributes={'word_num': data['word_num'][i]}
                    )
                    text_regions.append(text_element)
        
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
        
        return text_regions
    
    async def _detect_application_state(self, image: np.ndarray, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Detect the current application state"""
        state = {
            'has_dialog': len(analysis['dialogs']) > 0,
            'dialog_count': len(analysis['dialogs']),
            'button_count': len(analysis['buttons']),
            'likely_application': 'unknown'
        }
        
        # Detect application by window chrome or text
        for text_element in analysis.get('text_regions', []):
            text_lower = text_element.text.lower()
            if 'powerpoint' in text_lower:
                state['likely_application'] = 'powerpoint'
            elif 'excel' in text_lower:
                state['likely_application'] = 'excel'
            elif 'word' in text_lower:
                state['likely_application'] = 'word'
        
        # Detect Copilot dialog
        copilot_indicators = ['copilot', 'add a slide', 'generate']
        for element in analysis['elements']:
            if any(indicator in element.text.lower() for indicator in copilot_indicators):
                state['has_copilot_dialog'] = True
                state['copilot_location'] = element.bbox
                break
        
        return state
    
    async def find_element(self, element_description: str, screenshot_path: Optional[str] = None) -> Optional[UIElement]:
        """Find a specific UI element by description"""
        analysis = await self.analyze_screen(screenshot_path)
        
        description_lower = element_description.lower()
        
        # Search through all elements
        best_match = None
        best_score = 0
        
        for element in analysis['elements']:
            score = 0
            
            # Type match
            if element.type in description_lower:
                score += 0.3
            
            # Text match
            if element.text and element.text.lower() in description_lower:
                score += 0.5
            elif element.text and description_lower in element.text.lower():
                score += 0.3
            
            # Special cases
            if 'close' in description_lower and element.text == 'X':
                score += 0.5
            if 'dialog' in description_lower and element.type == 'dialog':
                score += 0.4
            
            # Update best match
            if score > best_score:
                best_score = score
                best_match = element
        
        return best_match if best_score > 0.3 else None
    
    async def wait_for_element(self, element_description: str, timeout: int = 10) -> Optional[UIElement]:
        """Wait for an element to appear"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            element = await self.find_element(element_description)
            if element:
                return element
            
            await asyncio.sleep(0.5)
            await self.capture(reason=f"waiting_for_{element_description}")
        
        return None
    
    async def verify_element_gone(self, element_description: str, timeout: int = 5) -> bool:
        """Verify an element has disappeared"""
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            element = await self.find_element(element_description)
            if not element:
                return True
            
            await asyncio.sleep(0.5)
            await self.capture(reason=f"verifying_{element_description}_gone")
        
        return False
    
    def get_click_position(self, element: UIElement) -> Tuple[int, int]:
        """Get the best position to click an element"""
        if element.type == 'button' and element.attributes.get('style') == 'close':
            # Click center of close button
            return element.center
        elif element.type == 'dialog':
            # Look for close button location
            if 'close_button_location' in element.attributes:
                return element.attributes['close_button_location']
            else:
                # Default to top-right of dialog
                x, y, w, h = element.bbox
                return (x + w - 20, y + 20)
        else:
            # Default to center
            return element.center

# Standalone test function
async def test_screen_analyzer():
    """Test the screen analyzer"""
    analyzer = ScreenAnalyzer()
    
    print("Screen Analyzer Test")
    print("===================")
    
    # Capture screen
    screenshot = await analyzer.capture(reason="test")
    print(f"Screenshot captured: {screenshot}")
    
    # Analyze screen
    print("\nAnalyzing screen...")
    analysis = await analyzer.analyze_screen()
    
    print(f"\nFound {len(analysis['dialogs'])} dialogs")
    print(f"Found {len(analysis['buttons'])} buttons")
    print(f"Found {len(analysis['text_regions'])} text regions")
    
    print("\nApplication state:")
    for key, value in analysis['state'].items():
        print(f"  {key}: {value}")
    
    # Test finding specific element
    print("\nLooking for close button...")
    close_button = await analyzer.find_element("close button")
    if close_button:
        print(f"Found close button at {close_button.center}")
    else:
        print("No close button found")
    
    # Look for Copilot dialog
    if analysis['state'].get('has_copilot_dialog'):
        print("\nCopilot dialog detected!")
        print(f"Location: {analysis['state'].get('copilot_location')}")

if __name__ == "__main__":
    asyncio.run(test_screen_analyzer())