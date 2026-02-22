# Video Editing Tools: API, Scripting, and Automation Potential

> **Research Date:** February 18, 2026
> **Purpose:** Evaluate automation and external AI orchestration integration potential for 5 video editing tools

---

## Summary Ranking (Most to Least Automatable)

| Rank | Tool | Score | Rationale |
|------|------|-------|-----------|
| 1 | **DaVinci Resolve** | 9.5/10 | Full Python/Lua scripting API, headless rendering, Fusion node scripting, local control, free |
| 2 | **Runway** | 8.5/10 | Official REST API + Python SDK, cloud-native, async task model, but generation-only (not editing) |
| 3 | **Adobe Premiere Pro** | 7/10 | UXP/ExtendScript APIs, MCP server projects exist, but no true headless mode, requires running GUI |
| 4 | **CapCut** | 4/10 | No official API; community reverse-engineered draft format; fragile, depends on undocumented internals |
| 5 | **Descript** | 3/10 | Minimal API (import/export only); no timeline manipulation; no CLI; Underlord is UI-only |

### Quick Decision Matrix

| Capability | DaVinci Resolve | Runway | Premiere Pro | CapCut | Descript |
|------------|:-:|:-:|:-:|:-:|:-:|
| Official API | Yes (Python/Lua) | Yes (REST + SDK) | Yes (UXP/ExtendScript) | No | Partial |
| Headless/CLI Rendering | Yes (-nogui) | Yes (cloud API) | No | No | No |
| Timeline Manipulation | Yes | N/A (generative) | Yes (limited) | Via draft files | No |
| Batch Processing | Yes | Yes | Via watch folders | Via draft generation | No |
| Webhooks/Callbacks | No (polling) | Polling (SDK built-in) | No | No | No |
| Free Tier for Dev | Yes (free version) | 125 credits one-time | No (subscription) | Free app | Free tier exists |
| MCP Server Available | Community | No | Community | Community | No |

---

## 1. DaVinci Resolve (Blackmagic Design)

### API Availability: EXCELLENT

DaVinci Resolve provides a comprehensive scripting API supporting both **Python** (2.7, 3.6+) and **Lua**. The API is bundled with the application (including the free version) and requires no additional licensing for scripting access.

**Object Model Hierarchy:**
```
Resolve
  +-- GetProjectManager() -> ProjectManager
        +-- GetCurrentProject() -> Project
              +-- GetMediaPool() -> MediaPool
              +-- GetCurrentTimeline() -> Timeline
              +-- AddRenderJob() -> string
              +-- StartRendering() -> Bool
```

**Key API Objects and Methods:**

| Object | Key Methods |
|--------|------------|
| `Resolve` | `GetProjectManager()`, `GetMediaStorage()`, `OpenPage()`, `Quit()` |
| `ProjectManager` | `CreateProject()`, `LoadProject()`, `GetCurrentProject()` |
| `Project` | `GetMediaPool()`, `GetCurrentTimeline()`, `AddRenderJob()`, `StartRendering()`, `StopRendering()`, `GetRenderJobs()`, `SetRenderSettings()` |
| `MediaPool` | `ImportMedia()`, `CreateTimelineFromClips()`, `AppendToTimeline()`, `CreateEmptyTimeline()` |
| `Timeline` | `GetName()`, `GetTrackCount()`, `GetItemListInTrack()`, `AddMarker()`, `Export()`, `SetCurrentTimecode()` |
| `TimelineItem` | `GetDuration()`, `GetStart()`, `SetProperty()`, `AddFusionComp()` |

### CLI/Headless Rendering: YES

DaVinci Resolve supports headless operation with the `-nogui` flag:

```bash
# Launch Resolve in headless mode (no UI)
"/opt/resolve/bin/resolve" -nogui

# Remote rendering mode
"/opt/resolve/bin/resolve" -rr
```

In headless mode, the scripting API remains fully functional. You can launch Resolve without a GUI, connect via Python, manipulate projects, and trigger renders programmatically.

### Scripting Capabilities: COMPREHENSIVE

**What can be automated:**
- Project creation and configuration (resolution, frame rate, color science)
- Media import and organization in bins
- Timeline creation from clips
- Appending clips to timelines
- Render settings configuration (format, codec, resolution)
- Batch rendering of multiple timelines
- Color grading operations
- Fusion composition creation and node manipulation
- Marker management
- Project export/import (DRP, XML, AAF, EDL)

**Known Limitations:**
- Clips can only be appended to Track 1 via API (no arbitrary track placement)
- No API method to move clips between tracks
- Some operations require the Studio (paid) version
- Fusion scripting is separate from the main Resolve API

### Code Example: Complete Automation Pipeline

```python
#!/usr/bin/env python3
"""DaVinci Resolve: Create project, import media, build timeline, render."""

import DaVinciResolveScript as dvr_script

# Connect to running Resolve instance
resolve = dvr_script.scriptapp("Resolve")
project_manager = resolve.GetProjectManager()

# Create a new project
project = project_manager.CreateProject("AutomatedProject_001")
if not project:
    project = project_manager.LoadProject("AutomatedProject_001")

# Set project settings
project.SetSetting("timelineResolutionWidth", "1920")
project.SetSetting("timelineResolutionHeight", "1080")
project.SetSetting("timelineFrameRate", "30")

# Import media
media_pool = project.GetMediaPool()
media_storage = resolve.GetMediaStorage()
media_storage.AddItemListToMediaPool([
    "/path/to/clip1.mp4",
    "/path/to/clip2.mp4",
    "/path/to/audio.wav"
])

# Create timeline from clips
root_folder = media_pool.GetRootFolder()
clips = root_folder.GetClipList()
timeline = media_pool.CreateTimelineFromClips("Main Timeline", clips)

# Configure render settings
project.SetRenderSettings({
    "SelectAllFrames": True,
    "TargetDir": "/output/renders/",
    "CustomName": "final_output",
    "FormatWidth": 1920,
    "FormatHeight": 1080,
    "FrameRate": 30.0,
})

# Add to render queue and start
project.AddRenderJob()
project.StartRendering()

# Poll render status
import time
while project.IsRenderingInProgress():
    time.sleep(2)
    jobs = project.GetRenderJobs()
    for job_id, job_info in jobs.items():
        print(f"Job {job_id}: {job_info.get('CompletionPercentage', 0)}%")

print("Render complete!")
```

### Fusion Scripting (VFX/Compositing)

Fusion provides its own scripting layer for node-based compositing:

```lua
-- Fusion Lua: Add a text overlay node to the current composition
local comp = fu:GetCurrentComp()
local text = comp:AddTool("TextPlus")
text.StyledText = "Automated Overlay"
text.Size = 0.05
text.Center = {0.5, 0.9}
```

Fusion scripts can be invoked from the console, via command line using `fuscript`, or dragged into the Nodes view.

### Integration Potential: HIGH

- **File watching:** Monitor a folder for new media, auto-import and render
- **Batch processing:** Script can iterate over multiple projects/timelines
- **Remote control:** `fuscript` allows remote scripting across network
- **Database support:** PostgreSQL database backend for multi-user collaboration
- **Pipeline integration:** DRP/XML/AAF/EDL import/export for interchange with other tools

### Documentation Quality: MODERATE

The official documentation is bundled as a text file with the application (`Readme.txt` in the scripting folder). It is functional but sparse. The community has created significantly better resources:

- [Unofficial API Docs (deric)](https://deric.github.io/DaVinciResolve-API-Docs/) - Best organized reference
- [X-Raym's API Doc](https://extremraym.com/cloud/resolve-scripting-doc/) - Comprehensive with version tracking
- [ResolveDevDoc](https://resolvedevdoc.readthedocs.io/) - ReadTheDocs format with examples
- [GitHub Examples](https://github.com/deric/DaVinciResolve-API-Docs/tree/main/examples) - Python and Lua examples
- [We Suck Less Forum](https://www.steakunderwater.com/wesuckless/viewforum.php?f=46) - Active scripting community

### Rate Limits and Pricing: N/A (Local Software)

- **DaVinci Resolve Free:** Full scripting API access, some render format limitations
- **DaVinci Resolve Studio:** $295 one-time purchase, all features unlocked
- No API call costs, no rate limits, no subscription

---

## 2. Runway (RunwayML)

### API Availability: EXCELLENT

Runway provides an official REST API and official SDKs for programmatic AI video generation. This is a **cloud-native generative API**, not a traditional video editor API.

**Official SDKs:**
- Python: `pip install runwayml` (Python 3.9+)
- JavaScript/TypeScript: `npm install @runwayml/sdk`

**API Base URL:** `https://api.dev.runwayml.com/v1/`

**Available Models (as of 2025-2026):**
- `gen4_turbo` - Latest fast generation model
- `gen3a_turbo` - Previous generation, faster
- `gen3a` - Previous generation, higher quality

**API Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/image_to_video` | POST | Generate video from image + prompt |
| `/text_to_video` | POST | Generate video from text prompt |
| `/tasks/{id}` | GET | Check task status and retrieve output |

### CLI/Headless Rendering: YES (Cloud-Native)

All generation happens in the cloud. No local GPU or application required. The API is inherently headless.

### Code Example: Image-to-Video Generation

```python
#!/usr/bin/env python3
"""Runway: Generate video from image using Gen-4 Turbo."""

from runwayml import RunwayML
import time

client = RunwayML()  # Uses RUNWAYML_API_SECRET env var

# Create image-to-video task
task = client.image_to_video.create(
    model="gen4_turbo",
    prompt_image="https://example.com/assets/scene.jpg",
    prompt_text="Camera slowly pans right, golden hour lighting, cinematic",
    ratio="1280:720",
    duration=10,  # seconds
)

print(f"Task ID: {task.id}")

# Poll for completion (SDK has built-in polling)
task_output = client.tasks.retrieve(task.id)
while task_output.status not in ["SUCCEEDED", "FAILED"]:
    time.sleep(5)
    task_output = client.tasks.retrieve(task.id)
    print(f"Status: {task_output.status}")

if task_output.status == "SUCCEEDED":
    print(f"Video URL: {task_output.output[0]}")
else:
    print(f"Failed: {task_output.failure}")
```

**Async Example:**

```python
import asyncio
from runwayml import AsyncRunwayML

client = AsyncRunwayML()

async def generate_video():
    task = await client.image_to_video.create(
        model="gen4_turbo",
        prompt_image="https://example.com/scene.jpg",
        prompt_text="Dramatic zoom into the subject",
        ratio="1280:720",
        duration=10,
    )
    # Built-in polling helper
    result = await task.wait_for_output(timeout=600)
    return result

asyncio.run(generate_video())
```

### Integration Potential: HIGH (for generation)

- **Async task model:** Submit many tasks, poll for results
- **No rate limiting per minute:** Only concurrent task limits
- **Automatic queuing:** Excess tasks are throttled but queued server-side
- **SDK polling helpers:** Built-in `wait_for_output` with configurable timeout
- **Batch workflows:** Generate multiple clips in parallel within concurrency limits

**Limitations for orchestration:**
- Generation only (no timeline editing, no compositing, no audio mixing)
- Output is individual video clips, not edited sequences
- No webhook callbacks (must poll for completion)
- Credits are consumed per generation, costs scale linearly

### Rate Limits and Pricing

**API Credits:** $0.01 per credit (purchased in developer portal)

| Generation Type | Credits | Cost |
|----------------|---------|------|
| Gen-4 10s clip | 120 credits | $1.20 |
| Gen-4 10s clip + 4K upscale | 140 credits | $1.40 |
| Gen-3 Alpha Turbo 10s | ~50 credits | $0.50 |

**Concurrency Tiers:**

| Tier | Daily Limit | Concurrent Tasks |
|------|-------------|------------------|
| Self-serve (default) | Varies | Limited (exact number not published) |
| Enterprise | Custom | Custom (higher limits) |

- No per-minute rate limit; concurrency-based throttling
- Throttled tasks are queued automatically (THROTTLED status)
- Enterprise tier available with custom limits via sales

### Documentation Quality: EXCELLENT

- [Official API Docs](https://docs.dev.runwayml.com/) - Clean, well-structured
- [API Reference](https://docs.dev.runwayml.com/api/) - Full endpoint documentation
- [Python SDK GitHub](https://github.com/runwayml/sdk-python) - Type-annotated, well-maintained
- [Getting Started Guide](https://docs.dev.runwayml.com/guides/using-the-api/) - Step-by-step
- [Pricing Guide](https://docs.dev.runwayml.com/guides/pricing/) - Transparent credit costs

---

## 3. Adobe Premiere Pro

### API Availability: GOOD (Complex Ecosystem)

Adobe Premiere Pro offers multiple scripting/extension frameworks:

**1. UXP (Unified Extensibility Platform) - Current/Recommended (2025+)**
- Modern JavaScript engine
- Available since Premiere v25.6 (graduated from beta Dec 2025)
- Async API calls (non-blocking, unlike ExtendScript)
- Access to project, sequences, clips, effects, export
- Official samples: [GitHub - AdobeDocs/uxp-premiere-pro-samples](https://github.com/AdobeDocs/uxp-premiere-pro-samples)

**2. ExtendScript - Legacy (supported through Sept 2026)**
- JavaScript-based (ES3 dialect)
- Synchronous calls (blocks UI during execution)
- Broader API surface than current UXP (UXP is still catching up)
- Well-documented via community: [ppro-scripting.docsforadobe.dev](https://ppro-scripting.docsforadobe.dev/)

**3. CEP (Common Extensibility Platform) - Deprecated**
- HTML/CSS/JS panels with ExtendScript backend
- Being replaced by UXP
- Still functional in current versions

### CLI/Headless Rendering: NO (Major Limitation)

Adobe Premiere Pro has **no headless rendering mode**. Unlike After Effects (`aerender`), there is no command-line renderer for Premiere Pro projects.

**Workarounds:**
- **Adobe Media Encoder Watch Folders:** Drop `.prproj` files into a watch folder for automatic encoding
- **Export via ExtendScript/UXP:** Trigger export programmatically while Premiere is running
- **PProHeadless:** A legacy utility that handles export via AME without the full Premiere UI, but requires AME to be running

### Scripting Capabilities

**What can be automated (ExtendScript/UXP):**
- Open/create projects and sequences
- Import media files and folders
- Add clips to sequences (with limitations)
- Apply effects and transitions
- Set effect parameters
- Configure and trigger export
- Read/write metadata and markers
- Duplicate and delete sequences

**Known Limitations:**
- Cannot move clips between tracks programmatically
- Limited audio keyframe control
- No direct timeline scrubbing/playback control
- UXP is still reaching feature parity with ExtendScript
- Requires Premiere Pro to be running with UI

### Code Example: ExtendScript Timeline Operations

```javascript
// ExtendScript: Import media, create sequence, export
var project = app.project;

// Import media
var importArray = ["/path/to/clip1.mp4", "/path/to/clip2.mp4"];
project.importFiles(importArray);

// Create a new sequence
var seq = project.createNewSequence("Automated Sequence", "seqID_001");

// Insert clips (requires clip objects from project items)
var rootItem = project.rootItem;
for (var i = 0; i < rootItem.children.numItems; i++) {
    var clip = rootItem.children[i];
    if (clip.type === ProjectItemType.CLIP) {
        seq.videoTracks[0].insertClip(clip, seq.end);
    }
}

// Trigger export via AME
var outputPath = "/output/export.mp4";
var presetPath = "/path/to/preset.epr";
project.activeSequence.exportAsMediaDirect(
    outputPath,
    presetPath,
    app.encoder.ENCODE_IN_TO_OUT
);
```

### MCP Server Integration (Community)

Multiple community MCP server projects exist for Premiere Pro:

- [hetpatel-11/Adobe_Premiere_Pro_MCP](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP) - UXP-based MCP bridge
- [mikechambers/adb-mcp](https://github.com/mikechambers/adb-mcp) - Adobe Creative Suite MCP

These allow AI agents (Claude, etc.) to control Premiere Pro via natural language. Current capabilities include media import, sequence creation, clip manipulation, effects application, and export triggering.

**Caveat:** These are experimental/proof-of-concept projects. UXP scripting in Premiere Pro is still maturing, and some operations may not be reliable.

### Integration Potential: MODERATE

- **Watch folder automation:** Adobe Media Encoder can monitor folders for automatic encoding
- **Panel-based automation:** UXP/CEP panels can run custom JavaScript logic
- **Inter-app communication:** ExtendScript can communicate between Premiere, After Effects, and AME
- **No webhooks or event system** for external triggers
- **Requires active Premiere Pro session** with GUI

### Documentation Quality: GOOD

- [Official UXP Docs](https://developer.adobe.com/premiere-pro/uxp/) - Clean, modern, but still growing
- [Premiere Pro API Reference](https://developer.adobe.com/premiere-pro/uxp/ppro_reference/) - Official UXP reference
- [Community Scripting Guide](https://ppro-scripting.docsforadobe.dev/) - Excellent ExtendScript reference
- [UXP Samples on GitHub](https://github.com/AdobeDocs/uxp-premiere-pro-samples) - Official examples
- [PProPanel Sample](https://github.com/AdobeDocs/uxp-premiere-pro-samples) - Reference implementation

### Rate Limits and Pricing

- **Adobe Creative Cloud subscription required:** $22.99/mo (Premiere Pro only) or $59.99/mo (All Apps)
- No per-API-call costs
- No rate limits (local execution)

---

## 4. CapCut (ByteDance)

### API Availability: POOR (No Official API)

CapCut does **not** provide a public API, SDK, or any official developer program. There is no documented way to programmatically control CapCut through official channels.

**Community Alternatives:**

1. **VectCutAPI** ([GitHub](https://github.com/sun-guannan/VectCutAPI))
   - Python-based open-source project
   - Reverse-engineers CapCut/Jianying draft file format
   - Dual interface: HTTP API server + MCP protocol
   - Generates draft folders compatible with CapCut desktop app
   - Supports: multi-track editing, keyframe animation, text overlays, transitions, filters

2. **CapCutAPI** ([GitHub](https://github.com/gogelabs/capcutapi))
   - Similar reverse-engineering approach
   - Draft file creation and modification
   - Material management (video, audio, images, text, stickers)

3. **CapCut MCP Servers** (multiple implementations)
   - [fancyboi999/capcut-mcp](https://lobehub.com/mcp/fancyboi999-capcut-mcp)
   - [kritsanan1/capcut-mcp](https://smithery.ai/server/kritsanan1/capcut-mcp)

### CLI/Headless Rendering: NO

CapCut has no headless mode and no command-line rendering capability. The community workaround via VectCutAPI involves:
1. Generate a draft folder programmatically
2. Copy the `dfd_*` folder to CapCut's drafts directory
3. Open CapCut and manually render (or use VectCutAPI's cloud rendering feature)

### Code Example: VectCutAPI Draft Generation

```python
# VectCutAPI: Create a CapCut-compatible draft programmatically
# (Based on VectCutAPI documentation)

import requests

# Start VectCutAPI HTTP server first
BASE_URL = "http://localhost:8000"

# Create a new draft
response = requests.post(f"{BASE_URL}/api/draft/create", json={
    "name": "AI Generated Video",
    "width": 1080,
    "height": 1920,
    "fps": 30
})
draft_id = response.json()["draft_id"]

# Add video material
requests.post(f"{BASE_URL}/api/material/add_video", json={
    "draft_id": draft_id,
    "file_path": "/path/to/video.mp4",
    "track_index": 0,
    "start_time": 0
})

# Add text overlay
requests.post(f"{BASE_URL}/api/material/add_text", json={
    "draft_id": draft_id,
    "content": "AI Generated Caption",
    "font_size": 48,
    "position": {"x": 0.5, "y": 0.85},
    "start_time": 0,
    "duration": 5000
})

# Save as CapCut draft
requests.post(f"{BASE_URL}/api/draft/save", json={
    "draft_id": draft_id,
    "output_dir": "/path/to/capcut/drafts/"
})
```

### Integration Potential: LOW

- **Draft file generation:** Create projects programmatically, but rendering requires the app
- **Fragile approach:** Relies on reverse-engineered undocumented file format
- **Encryption risk:** Newer versions of Jianying encrypt project files; CapCut may follow
- **No event system:** No webhooks, no file watching, no callbacks
- **Platform dependent:** Draft format may change without notice between versions

### Documentation Quality: POOR

- No official API documentation exists
- Community projects have README files and some MCP documentation
- [VectCutAPI README](https://github.com/sun-guannan/VectCutAPI/blob/main/README.md)
- [VectCutAPI MCP Documentation](https://github.com/sun-guannan/VectCutAPI/blob/main/MCP_Documentation_English.md)
- Reverse-engineered format may be incomplete or inaccurate

### Rate Limits and Pricing

- CapCut desktop app: Free
- CapCut Pro: $7.99/month (more effects, storage)
- No API costs (no official API)
- VectCutAPI: Open source (MIT license)

---

## 5. Descript

### API Availability: MINIMAL

Descript offers a very limited API focused primarily on **importing content into Descript** and **managing export targets**. It does not expose timeline editing, transcription, or AI features (Underlord) programmatically.

**Authentication:** Bearer token (personal API token, obtained by contacting Descript)

**API Base URL:** `https://descriptapi.com/v1/`

**Available Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/edit_in_descript/schema` | POST | Create import URL / import media into Descript |
| `/export_targets` | GET | List export targets |
| `/export_targets/{id}` | GET | Get specific export target |
| `/export_targets/{id}` | PUT | Update export target |
| `/export_targets/{id}` | DELETE | Delete export target |

### CLI/Headless Rendering: NO

Descript has no command-line interface, no headless mode, and no batch processing capability. All editing and rendering must be done through the desktop GUI.

### Scripting Capabilities: VERY LIMITED

**What can be automated:**
- Send media files (audio/video) to Descript for import
- Manage export destinations
- Supported formats: WAV, FLAC, MP3, MOV, MP4

**What CANNOT be automated:**
- Timeline editing or manipulation
- Transcription or text-based editing
- Underlord AI commands
- Effects application
- Audio cleanup (Studio Sound, etc.)
- Screen recording
- Filler word removal
- Any editing operations whatsoever

### Code Example: Import Media to Descript

```python
import requests

API_TOKEN = "your_personal_token_here"
BASE_URL = "https://descriptapi.com/v1"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Create an import schema to send media to Descript
payload = {
    "files": [
        {
            "url": "https://example.com/media/interview.mp4",
            "name": "Interview Recording"
        }
    ],
    "partner_drive_id": "external_system_id_123",
    "source_id": "batch_001"
}

response = requests.post(
    f"{BASE_URL}/edit_in_descript/schema",
    headers=headers,
    json=payload
)

# Returns a URL that opens Descript with the imported media
import_url = response.json().get("url")
print(f"Open in Descript: {import_url}")
```

### Underlord AI (Not API-Accessible)

Descript's Underlord is a powerful AI co-editor launched in August 2025 that can:
- Execute multi-step editing workflows from natural language ("make this ready for YouTube")
- Remove filler words, tighten pacing
- Add captions, transitions, B-roll
- Apply Studio Sound, Eye Contact effects
- Generate rough cuts automatically

However, Underlord is **exclusively available through the desktop UI**. There is no API, SDK, or programmatic access to Underlord capabilities. The community has actively requested open API access ([Feature Request](https://descript.canny.io/feature-requests/p/open-api-access)).

### Integration Potential: VERY LOW

- **Import-only workflow:** Can push files to Descript, but cannot control what happens next
- **n8n/Pipedream integration:** Available but limited to import/export operations via HTTP requests
- **No webhooks or callbacks** for render completion
- **No batch processing** capability
- **Manual intervention required** for all editing and export

### Documentation Quality: POOR

- [Official API Docs](https://docs.descriptapi.com/) - Minimal, covers only import/export
- [API Tracker](https://apitracker.io/a/descript) - Third-party listing
- No SDK provided
- No code examples in official docs
- Community has created basic integration examples for n8n and Pipedream

### Rate Limits and Pricing

- **Descript Free:** Limited features, 1 watermark-free export/month
- **Hobbyist:** $8/month
- **Business:** $33/month
- **Enterprise:** Custom pricing
- API access requires contacting Descript (not self-serve)
- No published API rate limits

---

## Integration Architecture Recommendations

### Recommended Architecture: AI Orchestrator + Tool Pipeline

```
                    +-------------------+
                    |  AI Orchestrator  |
                    |  (Claude/Agent)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |              |              |
     +--------v---+  +------v------+ +-----v-------+
     |   Runway   |  |  DaVinci    | |  Premiere   |
     |   API      |  |  Resolve    | |  Pro (UXP)  |
     | (Generate) |  | (Edit+Render| | (Edit+Render|
     +--------+---+  +------+------+ +-----+-------+
              |              |              |
              v              v              v
         AI-generated   Edited &       Edited &
         clips          rendered       rendered
              |         video          video
              |              |              |
              +--------------+--------------+
                             |
                    +--------v----------+
                    |   Output Storage  |
                    |   (Local/Cloud)   |
                    +-------------------+
```

### Tier 1: Production-Ready Automation

**DaVinci Resolve + Runway API** is the strongest combination:

1. **Runway API** generates AI video clips (text-to-video, image-to-video)
2. **DaVinci Resolve** (headless, Python-scripted) handles:
   - Importing generated clips
   - Timeline assembly
   - Color grading
   - Audio mixing
   - Effects and transitions
   - Final render output

```python
# Orchestration pseudo-code
async def produce_video(script, assets):
    # Step 1: Generate clips with Runway
    tasks = []
    for scene in script.scenes:
        task = runway_client.image_to_video.create(
            model="gen4_turbo",
            prompt_image=scene.reference_image,
            prompt_text=scene.description,
            duration=scene.duration,
        )
        tasks.append(task)

    # Step 2: Wait for all clips
    clips = await asyncio.gather(*[t.wait_for_output() for t in tasks])

    # Step 3: Download clips locally
    local_clips = [download(clip.output_url) for clip in clips]

    # Step 4: Assemble in DaVinci Resolve (headless)
    resolve = connect_to_resolve()  # running with -nogui
    project = resolve.GetProjectManager().CreateProject(script.title)
    media_pool = project.GetMediaPool()

    for clip_path in local_clips:
        media_pool.ImportMedia([clip_path])

    timeline = media_pool.CreateTimelineFromClips("Final",
        media_pool.GetRootFolder().GetClipList())

    # Step 5: Configure and render
    project.SetRenderSettings({
        "TargetDir": "/output/",
        "FormatWidth": 1920,
        "FormatHeight": 1080,
    })
    project.AddRenderJob()
    project.StartRendering()
```

### Tier 2: Adobe Ecosystem Integration

If already invested in Adobe Creative Cloud:

1. Use Premiere Pro UXP API for timeline editing
2. Use Adobe Media Encoder watch folders for batch rendering
3. Consider After Effects + `aerender` for motion graphics/VFX (After Effects has true CLI rendering)
4. Combine with Runway API for AI-generated content

### Tier 3: Lightweight / Social Media Focus

For short-form social content (TikTok, Reels, Shorts):

1. Use **Runway API** for clip generation
2. Use **VectCutAPI** to generate CapCut drafts with captions and effects
3. Manual review/render in CapCut for final output
4. This approach is fragile and not recommended for production pipelines

### What to Avoid

- **Descript** for automation pipelines (API too limited, no editing control)
- **CapCut** for production automation (no official API, reverse-engineered format)
- Any approach requiring manual UI interaction in the critical rendering path

---

## Real-World Automation Examples

### DaVinci Resolve

- [DaVinci-Resolve-Python-Automation](https://github.com/aman7mishra/DaVinci-Resolve-Python-Automation) - Full pipeline: media import, timeline creation, caption generation, rendering
- [Resolve Scripting Examples](https://github.com/deric/DaVinciResolve-API-Docs/tree/main/examples) - Grade and render all timelines, batch operations
- VFX pipelines commonly use Resolve scripting for review/approval workflows and automated color management

### Runway

- [Runway Automation on Apify](https://apify.com/igolaizola/runway-automation) - Cloud-based batch video generation
- [vidai](https://github.com/igolaizola/vidai) - Unofficial RunwayML Gen-2/Gen-3 client for batch generation
- Multiple AI video production companies use the Runway API as their generation backend

### Adobe Premiere Pro

- [Adobe Premiere Pro MCP Server](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP) - AI agent control of Premiere
- [adb-mcp](https://github.com/mikechambers/adb-mcp) - Multi-app Adobe MCP integration
- Enterprise broadcast workflows use ExtendScript for automated ingest and assembly

### CapCut

- [VectCutAPI](https://github.com/sun-guannan/VectCutAPI) - Enterprise-grade draft generation with MCP support
- Social media automation agencies use draft generation for scaled content production
- Several MCP server implementations for AI-assisted CapCut editing

---

## Sources and References

### DaVinci Resolve
- [DaVinci Resolve Scripting API Doc v20.3](https://gist.github.com/X-Raym/2f2bf453fc481b9cca624d7ca0e19de8)
- [Unofficial DaVinci Resolve API Docs](https://deric.github.io/DaVinciResolve-API-Docs/)
- [X-Raym's API Documentation](https://extremraym.com/cloud/resolve-scripting-doc/)
- [ResolveDevDoc (ReadTheDocs)](https://resolvedevdoc.readthedocs.io/en/latest/readme_resolveapi.html)
- [DaVinci Resolve Python API (GitHub)](https://github.com/diop/davinci-resolve-api)
- [Blackmagic Forum - Headless Mode](https://forum.blackmagicdesign.com/viewtopic.php?f=21&t=104557)
- [VFXPedia - Remote Rendering Setup](https://www.steakunderwater.com/VFXPedia/__man/Resolve18-6/DaVinciResolve18_Manual_files/part3963.htm)
- [DaVinci Resolve Fusion Scripting Guide (PDF)](https://documents.blackmagicdesign.com/UserManuals/Fusion8_Scripting_Guide.pdf)

### Runway
- [Runway API Documentation](https://docs.dev.runwayml.com/)
- [Runway API Reference](https://docs.dev.runwayml.com/api/)
- [Runway Python SDK (GitHub)](https://github.com/runwayml/sdk-python)
- [API Getting Started Guide](https://docs.dev.runwayml.com/guides/using-the-api/)
- [API Pricing & Costs](https://docs.dev.runwayml.com/guides/pricing/)
- [API Usage Tiers & Limits](https://docs.dev.runwayml.com/usage/tiers/)
- [Runway Developer Portal](https://dev.runwayml.com/)

### Adobe Premiere Pro
- [Premiere UXP API (Official)](https://developer.adobe.com/premiere-pro/uxp/)
- [Premiere Pro API Reference](https://developer.adobe.com/premiere-pro/uxp/ppro_reference/)
- [Premiere Pro Scripting Guide (Community)](https://ppro-scripting.docsforadobe.dev/)
- [UXP Samples (GitHub)](https://github.com/AdobeDocs/uxp-premiere-pro-samples)
- [UXP Arrives in Premiere (Adobe Blog)](https://blog.developer.adobe.com/en/publish/2025/12/uxp-arrives-in-premiere-a-new-era-for-plugin-development)
- [Premiere Pro MCP Server](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP)
- [Adobe MCP Integration](https://github.com/mikechambers/adb-mcp)

### CapCut
- [VectCutAPI (GitHub)](https://github.com/sun-guannan/VectCutAPI)
- [VectCutAPI MCP Documentation](https://github.com/sun-guannan/VectCutAPI/blob/main/MCP_Documentation_English.md)
- [CapCutAPI (GitHub)](https://github.com/gogelabs/capcutapi)
- [CapCut MCP Server (LobeHub)](https://lobehub.com/mcp/fancyboi999-capcut-mcp)
- [CapCut API Alternative - SamAutomation](https://samautomation.work/capcut-api/)
- [JSON2Video - CapCut API Guide](https://json2video.com/how-to/capcut-api/)

### Descript
- [Descript API Documentation](https://docs.descriptapi.com/)
- [Descript API Tracker](https://apitracker.io/a/descript)
- [Descript Integrations Page](https://www.descript.com/integrations)
- [Open API Access Feature Request](https://descript.canny.io/feature-requests/p/open-api-access)
- [Descript Underlord](https://www.descript.com/underlord)
- [n8n Descript Integration](https://n8n.io/integrations/descript/)
