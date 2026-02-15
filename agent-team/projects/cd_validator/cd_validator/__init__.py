"""
CD Validator - Construction Document Validation System

Validates construction documents against AIA standards, checks for broken references,
and ensures BIM naming conventions are followed.

Uses RevitMCPBridge for direct Revit integration via named pipe.
"""

__version__ = "1.0.0"
__author__ = "Christopher (Builder Agent)"

from cd_validator.core.base_validator import BaseValidator, ValidationResult, ValidationSeverity
from cd_validator.validators.sheet_validator import SheetValidator
from cd_validator.validators.reference_validator import ReferenceValidator
from cd_validator.validators.bim_standards_validator import BIMStandardsValidator

__all__ = [
    "BaseValidator",
    "ValidationResult",
    "ValidationSeverity",
    "SheetValidator",
    "ReferenceValidator",
    "BIMStandardsValidator",
]
