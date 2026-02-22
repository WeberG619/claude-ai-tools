"""
Embedded architectural knowledge for floor plan generation.

Data sourced from:
- room-standards.md
- single-family-residential.md
- kitchen-bath-design.md

All areas in sq ft. All dimensions in feet unless noted.
"""

from .models import RoomType, Zone


# =============================================================================
# ROOM SIZING BY TIER
# =============================================================================
# tier: small (800-1200), medium (1200-2200), large (2200-3000)
# Each entry: (min_area, target_area, max_area)

ROOM_SIZING = {
    RoomType.LIVING: {
        "small":  (150, 180, 250),
        "medium": (200, 270, 350),
        "large":  (250, 350, 500),
    },
    RoomType.KITCHEN: {
        "small":  (80, 110, 150),
        "medium": (120, 170, 250),
        "large":  (175, 250, 350),
    },
    RoomType.DINING: {
        "small":  (80, 100, 130),
        "medium": (100, 140, 200),
        "large":  (130, 180, 250),
    },
    RoomType.ENTRY: {
        "small":  (25, 35, 50),
        "medium": (35, 50, 70),
        "large":  (50, 70, 100),
    },
    RoomType.MASTER_BEDROOM: {
        "small":  (140, 170, 220),
        "medium": (180, 230, 300),
        "large":  (220, 300, 400),
    },
    RoomType.BEDROOM: {
        "small":  (100, 120, 150),
        "medium": (110, 140, 180),
        "large":  (130, 170, 220),
    },
    RoomType.MASTER_BATH: {
        "small":  (40, 55, 75),
        "medium": (60, 80, 120),
        "large":  (80, 120, 180),
    },
    RoomType.BATHROOM: {
        "small":  (35, 45, 60),
        "medium": (40, 55, 75),
        "large":  (50, 70, 100),
    },
    RoomType.HALF_BATH: {
        "small":  (18, 22, 30),
        "medium": (20, 28, 35),
        "large":  (24, 32, 40),
    },
    RoomType.LAUNDRY: {
        "small":  (25, 35, 50),
        "medium": (35, 50, 70),
        "large":  (50, 65, 90),
    },
    RoomType.HALLWAY: {
        "small":  (20, 30, 50),
        "medium": (30, 50, 80),
        "large":  (40, 65, 100),
    },
    RoomType.WALK_IN_CLOSET: {
        "small":  (20, 30, 40),
        "medium": (35, 48, 65),
        "large":  (48, 64, 100),
    },
    RoomType.PANTRY: {
        "small":  (12, 16, 25),
        "medium": (16, 24, 40),
        "large":  (24, 40, 60),
    },
    RoomType.OFFICE: {
        "small":  (80, 100, 130),
        "medium": (100, 130, 170),
        "large":  (120, 160, 220),
    },
    RoomType.FAMILY_ROOM: {
        "small":  (150, 200, 280),
        "medium": (200, 280, 400),
        "large":  (280, 380, 500),
    },
    RoomType.CLOSET: {
        "small":  (8, 12, 18),
        "medium": (12, 16, 24),
        "large":  (16, 24, 36),
    },
    RoomType.GARAGE: {
        "small":  (240, 264, 300),
        "medium": (300, 484, 576),
        "large":  (484, 576, 768),
    },
}


# =============================================================================
# ZONE CLASSIFICATION
# =============================================================================

ZONE_MAP = {
    RoomType.LIVING: Zone.PUBLIC,
    RoomType.KITCHEN: Zone.PUBLIC,
    RoomType.DINING: Zone.PUBLIC,
    RoomType.ENTRY: Zone.PUBLIC,
    RoomType.FAMILY_ROOM: Zone.PUBLIC,
    RoomType.MASTER_BEDROOM: Zone.PRIVATE,
    RoomType.BEDROOM: Zone.PRIVATE,
    RoomType.MASTER_BATH: Zone.PRIVATE,
    RoomType.BATHROOM: Zone.PRIVATE,
    RoomType.HALF_BATH: Zone.SERVICE,
    RoomType.LAUNDRY: Zone.SERVICE,
    RoomType.PANTRY: Zone.SERVICE,
    RoomType.OFFICE: Zone.PRIVATE,
    RoomType.HALLWAY: Zone.CIRCULATION,
    RoomType.CLOSET: Zone.PRIVATE,
    RoomType.WALK_IN_CLOSET: Zone.PRIVATE,
    RoomType.GARAGE: Zone.SERVICE,
}


# =============================================================================
# ADJACENCY MATRIX
# =============================================================================
# Weights: +2 = must be adjacent, +1 = preferred adjacent,
#           0 = neutral, -1 = prefer separated, -2 = must not be adjacent
# Only upper triangle stored; lookup function handles symmetry.

_ADJ_KEYS = [
    RoomType.LIVING, RoomType.KITCHEN, RoomType.DINING, RoomType.ENTRY,
    RoomType.MASTER_BEDROOM, RoomType.BEDROOM, RoomType.MASTER_BATH,
    RoomType.BATHROOM, RoomType.HALF_BATH, RoomType.LAUNDRY,
    RoomType.HALLWAY, RoomType.OFFICE, RoomType.FAMILY_ROOM,
]

_ADJ_MATRIX = {
    # Living connects to kitchen, dining, entry, hallway
    (RoomType.LIVING, RoomType.KITCHEN):        +2,
    (RoomType.LIVING, RoomType.DINING):         +2,
    (RoomType.LIVING, RoomType.ENTRY):          +2,
    (RoomType.LIVING, RoomType.HALLWAY):        +1,
    (RoomType.LIVING, RoomType.FAMILY_ROOM):    +1,
    (RoomType.LIVING, RoomType.MASTER_BEDROOM): -1,
    (RoomType.LIVING, RoomType.BATHROOM):       -1,

    # Kitchen connects to dining, pantry, laundry
    (RoomType.KITCHEN, RoomType.DINING):        +2,
    (RoomType.KITCHEN, RoomType.PANTRY):        +2,
    (RoomType.KITCHEN, RoomType.LAUNDRY):       +1,
    (RoomType.KITCHEN, RoomType.ENTRY):         +1,
    (RoomType.KITCHEN, RoomType.MASTER_BEDROOM): -2,
    (RoomType.KITCHEN, RoomType.BEDROOM):       -2,

    # Dining connects to kitchen, living
    (RoomType.DINING, RoomType.ENTRY):          +1,
    (RoomType.DINING, RoomType.BEDROOM):        -1,

    # Entry connects to hallway, half bath
    (RoomType.ENTRY, RoomType.HALLWAY):         +2,
    (RoomType.ENTRY, RoomType.HALF_BATH):       +1,

    # Master bedroom connects to master bath, walk-in closet
    (RoomType.MASTER_BEDROOM, RoomType.MASTER_BATH):    +2,
    (RoomType.MASTER_BEDROOM, RoomType.WALK_IN_CLOSET): +2,
    (RoomType.MASTER_BEDROOM, RoomType.HALLWAY):        +1,
    (RoomType.MASTER_BEDROOM, RoomType.KITCHEN):        -2,

    # Bedroom connects to hallway, bathroom
    (RoomType.BEDROOM, RoomType.HALLWAY):       +2,
    (RoomType.BEDROOM, RoomType.BATHROOM):      +1,
    (RoomType.BEDROOM, RoomType.KITCHEN):       -2,
    (RoomType.BEDROOM, RoomType.LAUNDRY):       -1,

    # Master bath is private
    (RoomType.MASTER_BATH, RoomType.BEDROOM):   -1,

    # Bathroom near bedrooms
    (RoomType.BATHROOM, RoomType.HALLWAY):      +1,
    (RoomType.BATHROOM, RoomType.LIVING):       -1,

    # Half bath near entry/public
    (RoomType.HALF_BATH, RoomType.HALLWAY):     +1,
    (RoomType.HALF_BATH, RoomType.LIVING):      +1,

    # Laundry near bedrooms/baths
    (RoomType.LAUNDRY, RoomType.HALLWAY):       +1,
    (RoomType.LAUNDRY, RoomType.BATHROOM):      +1,

    # Hallway connects everything
    (RoomType.HALLWAY, RoomType.OFFICE):        +1,

    # Office is quiet
    (RoomType.OFFICE, RoomType.KITCHEN):        -1,
    (RoomType.OFFICE, RoomType.LAUNDRY):        -1,
}


def adjacency_weight(a: RoomType, b: RoomType) -> int:
    """Get adjacency weight between two room types. Symmetric lookup."""
    if a == b:
        return 0
    return _ADJ_MATRIX.get((a, b), _ADJ_MATRIX.get((b, a), 0))


# =============================================================================
# ASPECT RATIO CONSTRAINTS
# =============================================================================
# (min_aspect, max_aspect) — aspect = long/short side

ASPECT_RATIOS = {
    RoomType.LIVING:          (1.0, 2.0),
    RoomType.KITCHEN:         (1.0, 2.5),
    RoomType.DINING:          (1.0, 1.8),
    RoomType.ENTRY:           (1.0, 2.5),
    RoomType.MASTER_BEDROOM:  (1.0, 1.8),
    RoomType.BEDROOM:         (1.0, 1.6),
    RoomType.MASTER_BATH:     (1.2, 2.5),
    RoomType.BATHROOM:        (1.2, 2.5),
    RoomType.HALF_BATH:       (1.5, 3.0),
    RoomType.LAUNDRY:         (1.0, 2.5),
    RoomType.HALLWAY:         (2.0, 8.0),
    RoomType.WALK_IN_CLOSET:  (1.0, 2.0),
    RoomType.PANTRY:          (1.0, 3.0),
    RoomType.OFFICE:          (1.0, 1.8),
    RoomType.FAMILY_ROOM:     (1.0, 2.0),
    RoomType.CLOSET:          (1.0, 3.0),
    RoomType.GARAGE:          (1.0, 1.5),
}


# =============================================================================
# MINIMUM ROOM DIMENSIONS (feet)
# =============================================================================

MIN_DIMENSIONS = {
    RoomType.LIVING:          (12, 12),
    RoomType.KITCHEN:         (7, 8),
    RoomType.DINING:          (9, 9),
    RoomType.ENTRY:           (4, 4),
    RoomType.MASTER_BEDROOM:  (12, 12),
    RoomType.BEDROOM:         (9, 10),
    RoomType.MASTER_BATH:     (5, 7),
    RoomType.BATHROOM:        (5, 7),
    RoomType.HALF_BATH:       (3, 5),
    RoomType.LAUNDRY:         (5, 5),
    RoomType.HALLWAY:         (3.5, 3.5),
    RoomType.WALK_IN_CLOSET:  (5, 5),
    RoomType.PANTRY:          (3, 3),
    RoomType.OFFICE:          (8, 8),
    RoomType.FAMILY_ROOM:     (12, 12),
    RoomType.CLOSET:          (2, 2),
    RoomType.GARAGE:          (12, 20),
}


# =============================================================================
# DOOR SPECIFICATIONS
# =============================================================================
# (width_inches, height_inches)

DOOR_SPECS = {
    "entry":           (36, 84),
    "interior":        (30, 80),
    "bedroom":         (30, 80),
    "bathroom":        (28, 80),
    "half_bath":       (28, 80),
    "closet":          (24, 80),
    "walk_in_closet":  (30, 80),
    "master_bedroom":  (32, 80),
    "master_bath":     (30, 80),
    "laundry":         (30, 80),
    "pantry":          (24, 80),
    "office":          (30, 80),
    "garage":          (32, 80),
}


def get_door_spec(room_type: RoomType, is_entry: bool = False) -> tuple:
    """Get (width_inches, height_inches) for a door to this room type."""
    if is_entry:
        return DOOR_SPECS["entry"]
    key = room_type.value
    for k, v in DOOR_SPECS.items():
        if k in key:
            return v
    return DOOR_SPECS["interior"]


# =============================================================================
# WINDOW RULES
# =============================================================================
# glazing_ratio: fraction of floor area that should be glazing
# sill_height: inches above floor
# needs_egress: bedroom egress window requirement

WINDOW_RULES = {
    RoomType.LIVING:          {"glazing_ratio": 0.12, "sill_height": 24, "needs_egress": False},
    RoomType.KITCHEN:         {"glazing_ratio": 0.10, "sill_height": 42, "needs_egress": False},
    RoomType.DINING:          {"glazing_ratio": 0.10, "sill_height": 24, "needs_egress": False},
    RoomType.MASTER_BEDROOM:  {"glazing_ratio": 0.10, "sill_height": 30, "needs_egress": True},
    RoomType.BEDROOM:         {"glazing_ratio": 0.10, "sill_height": 30, "needs_egress": True},
    RoomType.OFFICE:          {"glazing_ratio": 0.10, "sill_height": 30, "needs_egress": False},
    RoomType.FAMILY_ROOM:     {"glazing_ratio": 0.12, "sill_height": 24, "needs_egress": False},
    RoomType.BATHROOM:        {"glazing_ratio": 0.05, "sill_height": 48, "needs_egress": False},
    RoomType.MASTER_BATH:     {"glazing_ratio": 0.05, "sill_height": 48, "needs_egress": False},
}


# =============================================================================
# DEFAULT ROOM PROGRAMS
# =============================================================================
# Key: (bedrooms, tier) → list of (room_type, name)

DEFAULT_PROGRAMS = {
    (1, "small"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.MASTER_BEDROOM, "Bedroom"),
        (RoomType.BATHROOM, "Bathroom"),
        (RoomType.ENTRY, "Entry"),
    ],
    (2, "small"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BATHROOM, "Bathroom"),
        (RoomType.ENTRY, "Entry"),
    ],
    (2, "medium"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.DINING, "Dining Room"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.MASTER_BATH, "Master Bath"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BATHROOM, "Bathroom"),
        (RoomType.LAUNDRY, "Laundry"),
        (RoomType.ENTRY, "Entry"),
    ],
    (3, "small"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BEDROOM, "Bedroom 3"),
        (RoomType.BATHROOM, "Bathroom"),
        (RoomType.ENTRY, "Entry"),
    ],
    (3, "medium"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.DINING, "Dining Room"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.MASTER_BATH, "Master Bath"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BEDROOM, "Bedroom 3"),
        (RoomType.BATHROOM, "Bathroom"),
        (RoomType.HALF_BATH, "Half Bath"),
        (RoomType.LAUNDRY, "Laundry"),
        (RoomType.ENTRY, "Entry"),
    ],
    (3, "large"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.DINING, "Dining Room"),
        (RoomType.FAMILY_ROOM, "Family Room"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.MASTER_BATH, "Master Bath"),
        (RoomType.WALK_IN_CLOSET, "Walk-in Closet"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BEDROOM, "Bedroom 3"),
        (RoomType.BATHROOM, "Bathroom"),
        (RoomType.HALF_BATH, "Half Bath"),
        (RoomType.LAUNDRY, "Laundry"),
        (RoomType.OFFICE, "Office"),
        (RoomType.ENTRY, "Entry"),
    ],
    (4, "medium"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.DINING, "Dining Room"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.MASTER_BATH, "Master Bath"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BEDROOM, "Bedroom 3"),
        (RoomType.BEDROOM, "Bedroom 4"),
        (RoomType.BATHROOM, "Bathroom 1"),
        (RoomType.BATHROOM, "Bathroom 2"),
        (RoomType.LAUNDRY, "Laundry"),
        (RoomType.ENTRY, "Entry"),
    ],
    (4, "large"): [
        (RoomType.LIVING, "Living Room"),
        (RoomType.KITCHEN, "Kitchen"),
        (RoomType.DINING, "Dining Room"),
        (RoomType.FAMILY_ROOM, "Family Room"),
        (RoomType.MASTER_BEDROOM, "Master Bedroom"),
        (RoomType.MASTER_BATH, "Master Bath"),
        (RoomType.WALK_IN_CLOSET, "Walk-in Closet"),
        (RoomType.BEDROOM, "Bedroom 2"),
        (RoomType.BEDROOM, "Bedroom 3"),
        (RoomType.BEDROOM, "Bedroom 4"),
        (RoomType.BATHROOM, "Bathroom 1"),
        (RoomType.BATHROOM, "Bathroom 2"),
        (RoomType.HALF_BATH, "Half Bath"),
        (RoomType.LAUNDRY, "Laundry"),
        (RoomType.OFFICE, "Office"),
        (RoomType.ENTRY, "Entry"),
    ],
}


# =============================================================================
# OPEN PLAN GROUPS
# =============================================================================
# Room types that form open-plan living spaces (no walls between them)

OPEN_PLAN_GROUPS = [
    {RoomType.LIVING, RoomType.KITCHEN, RoomType.DINING},
    {RoomType.LIVING, RoomType.FAMILY_ROOM},
]


def get_default_program(bedrooms: int, tier: str):
    """Get default room program. Falls back to closest match."""
    key = (bedrooms, tier)
    if key in DEFAULT_PROGRAMS:
        return DEFAULT_PROGRAMS[key]

    # Try same bedrooms, different tier
    for t in ["medium", "small", "large"]:
        if (bedrooms, t) in DEFAULT_PROGRAMS:
            return DEFAULT_PROGRAMS[(bedrooms, t)]

    # Clamp bedrooms
    clamped = max(1, min(bedrooms, 4))
    for t in ["medium", "small", "large"]:
        if (clamped, t) in DEFAULT_PROGRAMS:
            return DEFAULT_PROGRAMS[(clamped, t)]

    return DEFAULT_PROGRAMS[(2, "small")]
