# Revit 2026 API Changes: Walls, Joining, and Element Placement

> **Research Date:** February 18, 2026
> **Revit Version:** 2026 (released April 2025)
> **Target:** Wall creation pipeline development

---

## Executive Summary

Revit 2026 introduces several significant API changes relevant to wall creation and management. The **Wall.Create() method signatures themselves are unchanged** from 2025, but the surrounding ecosystem has notable additions:

1. **New Wall Attachment API** -- Programmatic control of wall-to-element attachments (top/bottom) for the first time
2. **CompoundStructure layer priority control** -- New methods for layer priority without changing function
3. **Core layer no longer mandatory** -- Compound elements can be created without a core layer
4. **Curve.Intersect() overhaul** -- Old overloads deprecated, new `CurveIntersectResult` class added
5. **ElementId(Int32) constructor removed** -- Breaking change, must use Int64
6. **BuiltInParameter renames** -- `OMNICLASS_CODE` and `UNIFORMAT_CODE` renamed

---

## 1. Wall.Create() Method Signatures

### Status: UNCHANGED in 2026

The Wall.Create() static method overloads remain the same as in Revit 2025. No new overloads were added, and none were deprecated. The existing overloads are:

#### Overload 1: Simple wall with default type
```csharp
public static Wall Create(
    Document document,
    Curve curve,           // Line or Arc for straight/curved walls
    ElementId levelId,     // Level to place wall on
    bool structural        // True for structural wall
)
```

#### Overload 2: Wall with specified type, height, and offset
```csharp
public static Wall Create(
    Document document,
    Curve curve,              // Line or Arc defining the wall path
    ElementId wallTypeId,     // WallType element ID
    ElementId levelId,        // Level to place wall on
    double height,            // Wall height in feet
    double offset,            // Offset from level in feet
    bool flip,                // Flip wall orientation
    bool structural           // True for structural wall
)
```

#### Overload 3: Profile wall (non-rectangular)
```csharp
public static Wall Create(
    Document document,
    IList<Curve> profile,     // Closed loop of planar curves defining vertical profile
    ElementId wallTypeId,     // WallType element ID
    ElementId levelId,        // Level element ID
    bool structural           // True for structural wall
)
```

#### Overload 4: Profile wall with normal vector
```csharp
public static Wall Create(
    Document document,
    IList<Curve> profile,     // Closed loop of planar curves defining vertical profile
    ElementId wallTypeId,     // WallType element ID
    ElementId levelId,        // Level element ID
    bool structural,          // True for structural wall
    XYZ normal                // Vector perpendicular to profile plane
)
```

#### Overload 5: Simple wall (no level, no type -- minimal)
```csharp
public static Wall Create(
    Document document,
    IList<Curve> profile,     // Closed loop of planar curves
    bool structural           // True for structural wall
)
```

### Notes for Curved Walls
- The `Curve` parameter in overloads 1 and 2 accepts `Arc` objects for curved walls
- Elliptical walls are **not** supported (explicit exclusion in Revit 2026 docs)
- For profile walls, the `IList<Curve>` must form a closed, planar loop
- The normal vector (overload 4) determines inside vs. outside face orientation

### No New Curved Wall or Wall Sweep Overloads
There are **no new overloads** specifically for curved walls or wall sweeps in 2026. The `WallSweep` and `WallSweepInfo` classes remain unchanged.

---

## 2. New Wall Attachment API (NEW IN 2026)

This is the most significant wall-related addition in Revit 2026. For the first time, the API provides programmatic access to wall attachment settings (previously only available through the UI "Attach Top/Base" command).

### New Methods on Wall Class

```csharp
// Get IDs of all elements attached to this wall
public IList<ElementId> Wall.GetAttachmentIds()

// Attach wall to a target element (roof, floor, ceiling, toposolid, or wall)
public void Wall.AddAttachment(
    ElementId targetId,
    AttachmentLocation attachmentLocation  // Top or Bottom
)

// Remove attachment by target element
public void Wall.RemoveAttachment(ElementId targetId)

// Remove attachment by target element and location
public void Wall.RemoveAttachment(
    ElementId targetId,
    AttachmentLocation attachmentLocation
)

// Static validation: can this element be an attachment target?
public static bool Wall.IsValidTargetAttachment(
    Document document,
    ElementId wallId,
    ElementId targetId
)
```

### AttachmentLocation Enum (NEW)
```csharp
public enum AttachmentLocation
{
    Top,       // Attach at wall top
    Bottom     // Attach at wall base
}
```

### Valid Attachment Targets
- Roofs
- Floors
- Ceilings
- Toposolids
- Other walls

### Usage Example
```csharp
// Attach wall top to a roof
using (Transaction tx = new Transaction(doc, "Attach Wall"))
{
    tx.Start();

    if (Wall.IsValidTargetAttachment(doc, wall.Id, roof.Id))
    {
        wall.AddAttachment(roof.Id, AttachmentLocation.Top);
    }

    tx.Commit();
}

// Query existing attachments
IList<ElementId> attachedIds = wall.GetAttachmentIds();
```

### Impact on Wall Creation Pipeline
Previously, after `Wall.Create()`, you could not programmatically attach the wall to a roof or floor -- you had to use `PostCommand` or workarounds. Now you can create a wall and immediately attach it.

---

## 3. CompoundStructure Changes (NEW IN 2026)

### Core Layer No Longer Required

In all prior versions, every `CompoundStructure` required at least one core layer. In Revit 2026, this restriction is removed. This is significant for creating finish-only wall types.

**Impact:** APIs for creating, modifying, and deleting layers in `CompoundStructure` now support structures with zero core layers.

### New Layer Priority Methods

```csharp
// Get the priority of a specific layer
public int CompoundStructure.GetLayerPriority(int layerIndex)

// Set the priority of a specific layer
public void CompoundStructure.SetLayerPriority(int layerIndex, int priority)

// Check if a priority value is valid for a layer's function
public bool CompoundStructure.IsValidLayerPriority(int layerIndex, int priority)

// Reset a single layer to its default priority
public void CompoundStructure.ResetLayerPriority(int layerIndex)

// Reset all layers to their default priorities
public void CompoundStructure.ResetAllLayersPriorities()
```

### New Property on CompoundStructureLayer

```csharp
// Direct access to layer priority
public int CompoundStructureLayer.LayerPriority { get; set; }
```

### Key Behavior Change
Previously, the only way to change a layer's priority was to change its **function** (e.g., from `Structure` to `Finish 1`). Now you can set priority independently of function. This gives much more flexibility when creating wall types programmatically.

### Example: Creating a Finish-Only Wall Type
```csharp
// In Revit 2026, you can create a compound structure with NO core layer
CompoundStructure cs = CompoundStructure.CreateSimpleCompoundStructure(
    new List<CompoundStructureLayer>
    {
        new CompoundStructureLayer(0.5 / 12.0, MaterialFunctionAssignment.Finish1, materialId)
    }
);

// Set custom priority
cs.SetLayerPriority(0, 3);

// Apply to wall type
wallType.SetCompoundStructure(cs);
```

---

## 4. LocationCurve and Wall Join Handling

### Status: NO BREAKING CHANGES in 2026

The `LocationCurve` class and wall joining behavior are **unchanged** in Revit 2026. The following existing methods continue to work as before:

#### LocationCurve (Unchanged)
```csharp
LocationCurve.Curve           // Get/set the wall's location curve
LocationCurve.ElementsAtJoin  // Get elements at a join (indexed by end: 0 or 1)
LocationCurve.JoinType        // Get/set join type at an end
```

#### WallUtils (Unchanged)
```csharp
WallUtils.AllowWallJoinAtEnd(Wall wall, int end)
WallUtils.DisallowWallJoinAtEnd(Wall wall, int end)
WallUtils.IsWallJoinAllowedAtEnd(Wall wall, int end)
```

#### JoinGeometryUtils (Unchanged)
```csharp
JoinGeometryUtils.JoinGeometry(Document doc, Element a, Element b)
JoinGeometryUtils.UnjoinGeometry(Document doc, Element a, Element b)
JoinGeometryUtils.AreElementsJoined(Document doc, Element a, Element b)
JoinGeometryUtils.GetJoinedElements(Document doc, Element element)
JoinGeometryUtils.SwitchJoinOrder(Document doc, Element a, Element b)
JoinGeometryUtils.IsCuttingElementInJoin(Document doc, Element a, Element b)
```

### UI-Level Wall Join Improvements (Not API)
Revit 2026 introduces "Create Walls by Room" and "Create Walls by Segment" features in the UI, but these do **not** have corresponding new API methods. They are UI-only features.

---

## 5. Curve.Intersect() Overhaul (IMPORTANT FOR WALL GEOMETRY)

### Deprecated Overloads

The following old overloads are deprecated in 2026 and will be removed in a future version:

```csharp
// DEPRECATED -- use new overload with CurveIntersectResultOption.Simple
[Obsolete]
public SetComparisonResult Intersect(Curve curve)

// DEPRECATED -- use new overload
[Obsolete]
public SetComparisonResult Intersect(Curve curve, out IntersectionResultArray results)
```

### New Replacement API

```csharp
// New overload (Revit 2026)
public CurveIntersectResult Intersect(
    Curve curve,
    CurveIntersectResultOption option
)
```

### New Classes and Enums

#### CurveIntersectResultOption Enum (NEW)
```csharp
public enum CurveIntersectResultOption
{
    Simple,    // Only returns the intersection classification (faster)
    Detailed   // Returns full overlap point/range data
}
```

#### CurveIntersectResult Class (NEW)
```csharp
public class CurveIntersectResult
{
    // The classification of intersection between the two curves
    public SetComparisonResult Result { get; }

    // Get overlap points/ranges (only populated if Detailed option was used)
    public IList<CurveOverlapPoint> GetOverlaps()
}
```

#### CurveOverlapPoint Class (NEW)
```csharp
public class CurveOverlapPoint
{
    public CurveOverlapPointType Type { get; }  // Point or RangeEndpoint
    public XYZ Point { get; }                    // 3D intersection point
    public double Parameter1 { get; }            // Parameter on first curve
    public double Parameter2 { get; }            // Parameter on second curve
}
```

#### CurveOverlapPointType Enum (NEW)
```csharp
public enum CurveOverlapPointType
{
    Point,          // Single intersection point
    RangeEndpoint   // Endpoint of an overlap range
}
```

### Migration Example
```csharp
// OLD (deprecated)
SetComparisonResult result = curve1.Intersect(curve2);

// NEW (Revit 2026)
CurveIntersectResult result = curve1.Intersect(curve2, CurveIntersectResultOption.Simple);
if (result.Result == SetComparisonResult.Overlap)
{
    // Curves intersect
}

// NEW with detailed results
CurveIntersectResult detailed = curve1.Intersect(curve2, CurveIntersectResultOption.Detailed);
foreach (CurveOverlapPoint pt in detailed.GetOverlaps())
{
    XYZ intersectionPoint = pt.Point;
    double param1 = pt.Parameter1;
    double param2 = pt.Parameter2;
}
```

### Why This Matters for Wall Pipelines
If your wall creation code uses `Curve.Intersect()` to detect wall-wall intersections, find trim points, or determine join locations, you should migrate to the new overloads. The old ones will still work in 2026 but will generate deprecation warnings and may be removed in 2027.

---

## 6. Breaking Changes and Removed Members

### ElementId Constructor Removed (BREAKING)

```csharp
// REMOVED in 2026 -- will not compile
ElementId id = new ElementId(42);           // int (Int32) -- REMOVED

// Use instead:
ElementId id = new ElementId(42L);          // long (Int64) -- REQUIRED
```

### ElementId.IntegerValue Removed (BREAKING)

```csharp
// REMOVED in 2026
int val = elementId.IntegerValue;           // REMOVED

// Use instead:
long val = elementId.Value;                 // Int64 -- REQUIRED
```

**Migration note:** These were deprecated in Revit 2024 and are now fully removed in 2026. Any code using `ElementId(int)` or `IntegerValue` will fail to compile against the 2026 API.

### BuiltInParameter Renames (BREAKING)

| Old Name (pre-2026) | New Name (2026) | Notes |
|---|---|---|
| `OMNICLASS_CODE` | `CLASSIFICATION_CODE` | Matches UI rename |
| `UNIFORMAT_CODE` | `ASSEMBLY_CODE` | Matches UI rename |
| `OMNICLASS_DESCRIPTION` | `CLASSIFICATION_DESCRIPTION` | Matches UI rename |
| `UNIFORMAT_DESCRIPTION` | `ASSEMBLY_DESCRIPTION` | Matches UI rename |

Corresponding `ParameterTypeId` values were also updated:
- `ParameterTypeId.OmniClassCode` -> `ParameterTypeId.ClassificationCode`
- `ParameterTypeId.UniformatCode` -> `ParameterTypeId.AssemblyCode`

### Structural Length Parameter Rename
The `INSTANCE_LENGTH_PARAM` user-visible name changed from "Length" to "System Length" for structural beams and columns. The BuiltInParameter enum value itself is unchanged, but `LabelUtils.GetLabelFor()` will return the new name.

### Model Checker API Removed
The Model Checker API (`Autodesk.Revit.DB.ModelChecker` namespace) has been completely removed in Revit 2026.

---

## 7. Element Placement Validation

### Status: NO NEW GENERAL VALIDATION METHODS

Revit 2026 does **not** introduce new general-purpose element placement validation methods. The existing validation approaches remain:

#### Existing Methods (Unchanged)
```csharp
// Check if a wall type is valid for creation
WallType.IsValidStyle(WallKind kind)

// Validate wall cross-section
Wall.IsWallCrossSectionValid(Document doc, WallType wallType, double height)

// Check if wall can have a profile sketch
Wall.CanHaveProfileSketch()

// Validate compound structure
CompoundStructure.IsValid()

// The new attachment validation (2026)
Wall.IsValidTargetAttachment(Document doc, ElementId wallId, ElementId targetId)
```

#### Analytical Validation (NEW -- Not Wall-Specific)
```csharp
// New in 2026, but for analytical elements only
AnalyticalElement.IsValidTransform()
AnalyticalSurfaceBase.IsOuterContourValid()
```

---

## 8. Other Relevant Changes

### Rebar Cranking API (NEW)
Multiple new classes and members support rebar cranking. Some rebar hook/end-condition APIs were renamed:
- "Hook" references renamed to "Termination" in several API locations
- New `RebarCranking` class with methods for managing cranked rebar

### Electrical/Cable Tray APIs (NEW)
Significant additions for cables, conductors, and wires -- not wall-related but indicates the focus areas for this release.

### DocumentOpening Event Change
Events that were previously invoked when `Application.DocumentOpening` was canceled will **no longer fire** in cancellation situations. This is a behavior change, not a signature change.

### IFC Import Changes
`IFCHybridImport` methods deprecated and replaced with new IFC Import Options for AnyCAD processing mode.

---

## 9. Summary Table: What Changed for Wall Pipelines

| Area | Status | Action Required |
|---|---|---|
| `Wall.Create()` overloads | **Unchanged** | None |
| Wall attachment (top/base) | **New in 2026** | Adopt for roof/floor attachment |
| `CompoundStructure` priority | **New in 2026** | Adopt for wall type creation |
| Core layer requirement | **Removed in 2026** | Can create coreless structures |
| `LocationCurve` | **Unchanged** | None |
| `WallUtils` join methods | **Unchanged** | None |
| `JoinGeometryUtils` | **Unchanged** | None |
| `WallSweep` / `WallSweepInfo` | **Unchanged** | None |
| `Curve.Intersect()` | **Deprecated** | Migrate to new overload |
| `ElementId(int)` | **Removed** | Use `ElementId(long)` |
| `ElementId.IntegerValue` | **Removed** | Use `ElementId.Value` |
| `OMNICLASS_CODE` parameter | **Renamed** | Update references |
| Curved wall support | **Unchanged** | Still use `Arc` with `Wall.Create()` |
| Profile wall creation | **Unchanged** | Still use `IList<Curve>` overloads |

---

## 10. Sources and References

### Official Documentation
- [Revit 2026 API -- What's New (rvtdocs.com)](https://rvtdocs.com/2026/whatsnew)
- [API Changes 2026 (revitapidocs.com)](https://www.revitapidocs.com/2026/news)
- [Wall Methods -- Revit 2026 (revitapidocs.com)](https://www.revitapidocs.com/2026/f3ad9b32-007e-a113-d314-efb668071180.htm)
- [CompoundStructure Class -- Revit 2026 (revitapidocs.com)](https://www.revitapidocs.com/2026/dc1a081e-8dab-565f-145d-a429098d353c.htm)
- [Curve.Intersect -- Revit 2026 (revitapidocs.com)](https://www.revitapidocs.com/2026/90e86110-9bce-6e43-c18a-4d67380008bb.htm)
- [BuiltInFailures.WallFailures -- Revit 2026 (revitapidocs.com)](https://www.revitapidocs.com/2026/22d82d7e-a7d6-c096-991c-728df0b2d61c.htm)
- [Major Changes and Renovations to the Revit API (Autodesk Help)](https://help.autodesk.com/view/RVT/2026/ENU/?guid=8af227f4-b765-4430-97ce-16108dfe3788)
- [What's New in Revit 2026 (Autodesk Help)](https://help.autodesk.com/cloudhelp/2026/ENU/Revit-WhatsNew/files/GUID-C81929D7-02CB-4BF7-A637-9B98EC9EB38B.htm)

### API Changes from Prior Versions (for comparison)
- [API Changes 2025 (revitapidocs.com)](https://www.revitapidocs.com/2025/news)
- [API Changes 2025.3 (revitapidocs.com)](https://www.revitapidocs.com/2025.3/news)
- [What's New in the Revit 2025 API (Building Coder)](https://thebuildingcoder.typepad.com/blog/2024/04/whats-new-in-the-revit-2025-api.html)

### Community and Blog Sources
- [Revit 2026 API Docs Online (Nonica)](https://nonica.io/revit-2026-api-documentation/)
- [Create Walls By Room and By Segment (BIM Depot)](https://bim-depot.com/blogs/revit-information-center/revit-2026-adds-create-walls-by-room-and-by-segment)
- [Revit 2026 and Beyond (Autodesk University)](https://www.autodesk.com/autodesk-university/class/Revit-2026-and-Beyond-Whats-New-Improved-and-Unexpected-2025)
- [Erik Frits -- What's New in Revit API 2026 (LearnRevitAPI)](https://www.learnrevitapi.com/newsletter/what-s-new-in-revit-api-2026-here-are-the-biggest-changes)
- [Retrieve Roof ID from Wall Attachment (Autodesk Forum)](https://forums.autodesk.com/t5/revit-api-forum/retrieve-roof-id-from-a-wall-attachment-revit-2026-pyrevit/td-p/13865665)

### Reference Documentation (Stable APIs)
- [Revit API Docs Home (revitapidocs.com)](https://www.revitapidocs.com/2026/)
- [Revit API Documentation (rvtdocs.com)](https://rvtdocs.com/)

---

## Appendix: Wall.Create Quick Reference for Pipeline

For a wall creation pipeline targeting Revit 2026, here is the recommended approach:

```csharp
public static Wall CreateWallInPipeline(
    Document doc,
    Curve locationCurve,    // Line for straight, Arc for curved
    ElementId wallTypeId,
    ElementId levelId,
    double height,          // In feet (internal units)
    double offset,          // Offset from level in feet
    bool isStructural)
{
    Wall wall = null;

    using (Transaction tx = new Transaction(doc, "Create Wall"))
    {
        tx.Start();

        wall = Wall.Create(
            doc,
            locationCurve,
            wallTypeId,
            levelId,
            height,
            offset,
            false,          // flip
            isStructural
        );

        tx.Commit();
    }

    return wall;
}

// For wall joining after creation:
public static void ConfigureWallJoins(Document doc, Wall wall, bool allowJoinAtStart, bool allowJoinAtEnd)
{
    using (Transaction tx = new Transaction(doc, "Configure Joins"))
    {
        tx.Start();

        if (allowJoinAtStart)
            WallUtils.AllowWallJoinAtEnd(wall, 0);
        else
            WallUtils.DisallowWallJoinAtEnd(wall, 0);

        if (allowJoinAtEnd)
            WallUtils.AllowWallJoinAtEnd(wall, 1);
        else
            WallUtils.DisallowWallJoinAtEnd(wall, 1);

        tx.Commit();
    }
}

// NEW in 2026: Attach wall to roof
public static void AttachWallToRoof(Document doc, Wall wall, ElementId roofId)
{
    using (Transaction tx = new Transaction(doc, "Attach to Roof"))
    {
        tx.Start();

        if (Wall.IsValidTargetAttachment(doc, wall.Id, roofId))
        {
            wall.AddAttachment(roofId, AttachmentLocation.Top);
        }

        tx.Commit();
    }
}
```
