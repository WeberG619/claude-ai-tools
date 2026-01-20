#!/usr/bin/env python3
"""
Site Intelligence - Unified Interface for Complete Site Analysis

This module integrates:
- 11 Site Data APIs (geocoding, elevation, flood, weather, soil, sun, parcel, storm, environmental, demographics, context)
- Project Database (SQLite-based project tracking)
- Professional Report Generator (PDF reports)
- Florida Zoning Database (development standards)

Designed for architectural workflow integration - get all site information with one call.
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Import all components
try:
    from site_data_full import get_complete_site_data, CompleteSiteData
except ImportError:
    get_complete_site_data = None

try:
    from project_database import ProjectDatabase
except ImportError:
    ProjectDatabase = None

try:
    from report_generator import generate_site_report, ReportConfig
except ImportError:
    generate_site_report = None

try:
    from florida_zoning import FloridaZoningDatabase, get_zoning_for_site
except ImportError:
    FloridaZoningDatabase = None

# NEW: Permit and Compliance Modules
try:
    from code_compliance import CodeComplianceDatabase, Discipline, ItemStatus
except ImportError:
    CodeComplianceDatabase = None

try:
    from permit_tracker import PermitTracker, PermitType, PermitStatus
except ImportError:
    PermitTracker = None

try:
    from jurisdiction_db import JurisdictionDatabase
except ImportError:
    JurisdictionDatabase = None

try:
    from comment_response import CommentResponseSystem, CommentCategory, ResponseType
except ImportError:
    CommentResponseSystem = None

# NEW: Optional Enhancement Modules
try:
    from noa_database import NOADatabase
except ImportError:
    NOADatabase = None

try:
    from fee_calculator import PermitFeeCalculator
except ImportError:
    PermitFeeCalculator = None

try:
    from permit_application_pdf import PermitApplicationPDF, ProjectInfo, OwnerInfo, ContractorInfo, ArchitectInfo, ApplicationType
except ImportError:
    PermitApplicationPDF = None
    ProjectInfo = None
    OwnerInfo = None
    ContractorInfo = None
    ArchitectInfo = None
    ApplicationType = None

try:
    from revit_schedule_integration import RevitScheduleValidator, validate_revit_schedules
except ImportError:
    RevitScheduleValidator = None
    validate_revit_schedules = None


# Default paths
DEFAULT_PROJECT_DB = os.path.join(os.path.dirname(__file__), "projects.db")
DEFAULT_ZONING_DB = os.path.join(os.path.dirname(__file__), "florida_zoning.db")
DEFAULT_REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
DEFAULT_COMPLIANCE_DB = os.path.join(os.path.dirname(__file__), "code_compliance.db")
DEFAULT_PERMIT_DB = os.path.join(os.path.dirname(__file__), "permit_tracker.db")
DEFAULT_JURISDICTION_DB = os.path.join(os.path.dirname(__file__), "jurisdiction_requirements.db")
DEFAULT_COMMENTS_DB = os.path.join(os.path.dirname(__file__), "comment_response.db")


class SiteIntelligence:
    """
    Unified interface for complete site analysis and project management

    Usage:
        si = SiteIntelligence()

        # Quick site lookup
        data = si.analyze_site("11900 SW 216th St, Goulds, FL")

        # Create project with full analysis
        project = si.create_project_with_analysis(
            address="11900 SW 216th St, Goulds, FL",
            project_name="Goulds Development",
            client_name="Test Client"
        )

        # Generate professional report
        report_path = si.generate_report(project['id'])
    """

    def __init__(
        self,
        project_db_path: str = None,
        zoning_db_path: str = None,
        reports_dir: str = None,
        compliance_db_path: str = None,
        permit_db_path: str = None,
        jurisdiction_db_path: str = None,
        comments_db_path: str = None,
        company_name: str = "BD Architect LLC",
        company_address: str = "Miami, Florida"
    ):
        self.project_db_path = project_db_path or DEFAULT_PROJECT_DB
        self.zoning_db_path = zoning_db_path or DEFAULT_ZONING_DB
        self.reports_dir = reports_dir or DEFAULT_REPORTS_DIR
        self.compliance_db_path = compliance_db_path or DEFAULT_COMPLIANCE_DB
        self.permit_db_path = permit_db_path or DEFAULT_PERMIT_DB
        self.jurisdiction_db_path = jurisdiction_db_path or DEFAULT_JURISDICTION_DB
        self.comments_db_path = comments_db_path or DEFAULT_COMMENTS_DB
        self.company_name = company_name
        self.company_address = company_address

        # Ensure reports directory exists
        os.makedirs(self.reports_dir, exist_ok=True)

        # Initialize components (lazy-loaded)
        self._project_db = None
        self._zoning_db = None
        self._compliance_db = None
        self._permit_tracker = None
        self._jurisdiction_db = None
        self._comment_system = None
        self._noa_db = None
        self._fee_calculator = None
        self._pdf_generator = None
        self._schedule_validator = None

    @property
    def project_db(self) -> 'ProjectDatabase':
        """Lazy-load project database"""
        if self._project_db is None and ProjectDatabase:
            self._project_db = ProjectDatabase(self.project_db_path)
        return self._project_db

    @property
    def zoning_db(self) -> 'FloridaZoningDatabase':
        """Lazy-load zoning database"""
        if self._zoning_db is None and FloridaZoningDatabase:
            self._zoning_db = FloridaZoningDatabase(self.zoning_db_path)
            # Populate if empty
            if not self._zoning_db.get_all_districts():
                self._zoning_db.populate_default_data()
        return self._zoning_db

    @property
    def compliance_db(self) -> 'CodeComplianceDatabase':
        """Lazy-load code compliance database"""
        if self._compliance_db is None and CodeComplianceDatabase:
            self._compliance_db = CodeComplianceDatabase(self.compliance_db_path)
        return self._compliance_db

    @property
    def permit_tracker(self) -> 'PermitTracker':
        """Lazy-load permit tracker"""
        if self._permit_tracker is None and PermitTracker:
            self._permit_tracker = PermitTracker(self.permit_db_path)
        return self._permit_tracker

    @property
    def jurisdiction_db(self) -> 'JurisdictionDatabase':
        """Lazy-load jurisdiction database"""
        if self._jurisdiction_db is None and JurisdictionDatabase:
            self._jurisdiction_db = JurisdictionDatabase(self.jurisdiction_db_path)
        return self._jurisdiction_db

    @property
    def comment_system(self) -> 'CommentResponseSystem':
        """Lazy-load comment response system"""
        if self._comment_system is None and CommentResponseSystem:
            self._comment_system = CommentResponseSystem(self.comments_db_path)
        return self._comment_system

    @property
    def noa_db(self) -> 'NOADatabase':
        """Lazy-load NOA database"""
        if self._noa_db is None and NOADatabase:
            self._noa_db = NOADatabase()
        return self._noa_db

    @property
    def fee_calculator(self) -> 'PermitFeeCalculator':
        """Lazy-load fee calculator"""
        if self._fee_calculator is None and PermitFeeCalculator:
            self._fee_calculator = PermitFeeCalculator()
        return self._fee_calculator

    @property
    def pdf_generator(self) -> 'PermitApplicationPDF':
        """Lazy-load PDF generator"""
        if self._pdf_generator is None and PermitApplicationPDF:
            self._pdf_generator = PermitApplicationPDF()
        return self._pdf_generator

    @property
    def schedule_validator(self) -> 'RevitScheduleValidator':
        """Lazy-load Revit schedule validator"""
        if self._schedule_validator is None and RevitScheduleValidator:
            self._schedule_validator = RevitScheduleValidator()
        return self._schedule_validator

    def analyze_site(
        self,
        address: str = None,
        lat: float = None,
        lon: float = None,
        include_zoning: bool = True,
        zoning_district: str = None,
        county: str = "Miami-Dade"
    ) -> Dict[str, Any]:
        """
        Perform complete site analysis

        Args:
            address: Street address (will be geocoded)
            lat: Latitude (if known)
            lon: Longitude (if known)
            include_zoning: Include zoning data (default True)
            zoning_district: Known zoning district code (e.g., "RU-1")
            county: County for zoning lookup (default Miami-Dade)

        Returns:
            Dictionary with all site data
        """
        result = {
            "timestamp": datetime.now().isoformat(),
            "input": {"address": address, "lat": lat, "lon": lon}
        }

        # Get site data from 11 APIs
        if get_complete_site_data:
            try:
                site_data = get_complete_site_data(address=address, lat=lat, lon=lon)
                if hasattr(site_data, '__dict__'):
                    result["site_data"] = asdict(site_data)
                else:
                    result["site_data"] = site_data
                result["site_data_success"] = True
            except Exception as e:
                result["site_data_success"] = False
                result["site_data_error"] = str(e)
        else:
            result["site_data_success"] = False
            result["site_data_error"] = "site_data_full module not available"

        # Get zoning data if requested
        if include_zoning and self.zoning_db and zoning_district:
            try:
                zoning_info = get_zoning_for_site(county, zoning_district)
                result["zoning"] = zoning_info
                result["zoning_success"] = zoning_info.get("found", False)
            except Exception as e:
                result["zoning_success"] = False
                result["zoning_error"] = str(e)

        # Generate summary
        result["summary"] = self._generate_analysis_summary(result)

        return result

    def create_project_with_analysis(
        self,
        address: str,
        project_name: str = None,
        client_name: str = None,
        zoning_district: str = None,
        county: str = "Miami-Dade",
        generate_report: bool = True
    ) -> Dict[str, Any]:
        """
        Create a new project and perform complete site analysis

        Args:
            address: Site address
            project_name: Project name (auto-generated if not provided)
            client_name: Client name
            zoning_district: Known zoning code
            county: County name
            generate_report: Generate PDF report automatically

        Returns:
            Dictionary with project info and analysis results
        """
        if not self.project_db:
            return {"error": "Project database not available"}

        # Create project
        project_id = self.project_db.create_project(
            name=project_name or f"Project at {address}",
            address=address,
            client_name=client_name
        )

        # Perform site analysis
        analysis = self.analyze_site(
            address=address,
            include_zoning=True,
            zoning_district=zoning_district,
            county=county
        )

        # Store site data in project
        if analysis.get("site_data_success"):
            self.project_db.store_site_data(project_id, analysis)

            # Update project coordinates
            site_data = analysis.get("site_data", {})
            if site_data:
                self.project_db.update_project(
                    project_id,
                    latitude=site_data.get("latitude"),
                    longitude=site_data.get("longitude")
                )

        # Generate report if requested
        report_path = None
        if generate_report and analysis.get("site_data_success"):
            try:
                report_path = self.generate_report(
                    project_id=project_id,
                    site_data=analysis.get("site_data"),
                    project_name=project_name,
                    client_name=client_name
                )
            except Exception as e:
                analysis["report_error"] = str(e)

        # Get updated project info
        project = self.project_db.get_project(project_id)

        return {
            "project": project,
            "analysis": analysis,
            "report_path": report_path
        }

    def generate_report(
        self,
        project_id: int = None,
        site_data: Dict = None,
        project_name: str = None,
        project_number: str = None,
        client_name: str = None,
        output_path: str = None
    ) -> str:
        """
        Generate a professional PDF report

        Args:
            project_id: Project ID (will load data from database)
            site_data: Site data dictionary (alternative to project_id)
            project_name: Project name for report
            project_number: Project number for report
            client_name: Client name for report
            output_path: Custom output path (default: reports directory)

        Returns:
            Path to generated PDF
        """
        if not generate_site_report:
            raise ImportError("Report generator not available")

        # Load from project database if project_id provided
        if project_id and self.project_db:
            project = self.project_db.get_project(project_id)
            if project:
                project_name = project_name or project.get("name")
                project_number = project_number or project.get("project_number")
                client_name = client_name or project.get("client_name")

                # Load site data from database
                if not site_data:
                    analyses = self.project_db.get_site_analyses(project_id)
                    if analyses:
                        latest = analyses[0]
                        site_data = json.loads(latest.get("site_data_json", "{}"))

        if not site_data:
            raise ValueError("No site data available for report")

        # Flatten site_data if nested
        if "site_data" in site_data:
            site_data = site_data["site_data"]

        # Generate output path
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = (project_name or "site_report").replace(" ", "_")[:30]
            output_path = os.path.join(self.reports_dir, f"{safe_name}_{timestamp}.pdf")

        # Configure report
        config = ReportConfig(
            company_name=self.company_name,
            company_address=self.company_address
        )

        # Generate report
        return generate_site_report(
            site_data=site_data,
            output_path=output_path,
            project_name=project_name,
            project_number=project_number,
            client_name=client_name,
            config=config
        )

    def lookup_zoning(
        self,
        county: str,
        district_code: str
    ) -> Dict[str, Any]:
        """
        Look up zoning district information

        Args:
            county: County name (Miami-Dade, Broward, Palm Beach)
            district_code: Zoning district code (e.g., RU-1, RS-2)

        Returns:
            Zoning district details
        """
        if not self.zoning_db:
            return {"error": "Zoning database not available"}

        return get_zoning_for_site(county, district_code)

    def find_zoning_by_criteria(
        self,
        county: str = None,
        category: str = None,
        min_density: float = None,
        max_height: int = None,
        use: str = None
    ) -> List[Dict]:
        """
        Find zoning districts matching criteria

        Args:
            county: County name
            category: District category (residential, commercial, industrial)
            min_density: Minimum density (units/acre)
            max_height: Maximum building height needed (ft)
            use: Use type to search for

        Returns:
            List of matching districts
        """
        if not self.zoning_db:
            return []

        return self.zoning_db.search_districts(
            county=county,
            category=category,
            min_density=min_density,
            max_height=max_height,
            use=use
        )

    def get_project(self, project_id: int = None, project_number: str = None) -> Optional[Dict]:
        """Get project by ID or number"""
        if not self.project_db:
            return None
        return self.project_db.get_project(project_id, project_number)

    def search_projects(
        self,
        query: str = None,
        status: str = None,
        client_name: str = None
    ) -> List[Dict]:
        """Search projects"""
        if not self.project_db:
            return []
        return self.project_db.search_projects(query, status, client_name)

    # =========================================================================
    # PERMIT & COMPLIANCE METHODS
    # =========================================================================

    def create_project_checklists(
        self,
        project_id: int,
        project_type: str = "commercial",
        hvhz: bool = True,
        flood_zone: bool = False,
        disciplines: List[str] = None
    ) -> Dict[str, Any]:
        """
        Create code compliance checklists for a project

        Args:
            project_id: Project ID
            project_type: Type of project (residential, commercial, mixed_use)
            hvhz: Is project in HVHZ zone
            flood_zone: Is project in flood zone
            disciplines: List of disciplines (default: all)

        Returns:
            Dictionary with checklist IDs and summary
        """
        if not self.compliance_db:
            return {"error": "Code compliance module not available"}

        if disciplines is None:
            disciplines = ["building", "structural", "mechanical",
                          "plumbing", "electrical", "fire"]

        result = {
            "project_id": project_id,
            "checklists_created": [],
            "total_items": 0
        }

        for discipline in disciplines:
            checklist_id = self.compliance_db.create_project_checklist(
                project_id=project_id,
                discipline=discipline,
                project_type=project_type,
                hvhz=hvhz,
                flood_zone=flood_zone
            )
            items = self.compliance_db.get_project_checklist(project_id, discipline)
            result["checklists_created"].append({
                "discipline": discipline,
                "checklist_id": checklist_id,
                "item_count": len(items)
            })
            result["total_items"] += len(items)

        return result

    def get_checklist_summary(self, project_id: int) -> Dict[str, Any]:
        """Get compliance checklist summary for a project"""
        if not self.compliance_db:
            return {"error": "Code compliance module not available"}
        return self.compliance_db.get_checklist_summary(project_id)

    def create_permit_application(
        self,
        project_id: int,
        permit_type: str,
        jurisdiction: str,
        **kwargs
    ) -> int:
        """
        Create a permit application for a project

        Args:
            project_id: Project ID
            permit_type: Type (building, electrical, mechanical, plumbing, etc.)
            jurisdiction: Jurisdiction name
            **kwargs: Additional permit parameters

        Returns:
            Permit application ID
        """
        if not self.permit_tracker:
            raise RuntimeError("Permit tracker not available")

        return self.permit_tracker.create_permit_application(
            project_id=project_id,
            permit_type=permit_type,
            jurisdiction=jurisdiction,
            **kwargs
        )

    def get_permit_status(self, permit_id: int) -> Optional[Dict]:
        """Get permit application details"""
        if not self.permit_tracker:
            return None
        return self.permit_tracker.get_permit_application(permit_id)

    def get_project_permits(self, project_id: int) -> List[Dict]:
        """Get all permits for a project"""
        if not self.permit_tracker:
            return []
        return self.permit_tracker.get_project_permits(project_id)

    def get_jurisdiction_info(self, jurisdiction_name: str) -> Optional[Dict]:
        """Get jurisdiction requirements and contact info"""
        if not self.jurisdiction_db:
            return None
        return self.jurisdiction_db.get_jurisdiction(name=jurisdiction_name)

    def get_jurisdictions_by_county(self, county: str) -> List[Dict]:
        """Get all jurisdictions in a county"""
        if not self.jurisdiction_db:
            return []
        return self.jurisdiction_db.get_all_jurisdictions(county=county)

    def compare_jurisdictions(
        self,
        jurisdiction_names: List[str],
        permit_type: str = "building"
    ) -> Dict[str, Any]:
        """Compare requirements across multiple jurisdictions"""
        if not self.jurisdiction_db:
            return {"error": "Jurisdiction database not available"}

        jur_ids = []
        for name in jurisdiction_names:
            jur = self.jurisdiction_db.get_jurisdiction(name=name)
            if jur:
                jur_ids.append(jur['id'])

        return self.jurisdiction_db.compare_jurisdictions(jur_ids, permit_type)

    def add_review_comments(
        self,
        project_id: int,
        comments: List[Dict],
        cycle_number: int = 1
    ) -> List[int]:
        """
        Add review comments from building department

        Args:
            project_id: Project ID
            comments: List of comment dictionaries with keys:
                      - discipline: building, structural, etc.
                      - text: comment text
                      - code_section: (optional) code reference
                      - sheet_reference: (optional) sheet reference
            cycle_number: Review cycle number

        Returns:
            List of comment IDs
        """
        if not self.comment_system:
            return []
        return self.comment_system.add_batch_comments(
            project_id, comments, cycle_number
        )

    def get_suggested_responses(self, comment_id: int) -> List[Dict]:
        """Get suggested responses for a review comment"""
        if not self.comment_system:
            return []
        return self.comment_system.suggest_response(comment_id)

    def generate_response_letter(
        self,
        project_id: int,
        cycle_number: int,
        project_name: str = None,
        project_address: str = None,
        permit_number: str = None,
        preparer_name: str = None
    ) -> str:
        """Generate formal response letter to review comments"""
        if not self.comment_system:
            return "Comment response system not available"
        return self.comment_system.generate_response_letter(
            project_id=project_id,
            cycle_number=cycle_number,
            project_name=project_name,
            project_address=project_address,
            permit_number=permit_number,
            preparer_name=preparer_name,
            company_name=self.company_name
        )

    def start_permitting_workflow(
        self,
        project_id: int,
        jurisdiction: str,
        permit_types: List[str] = None,
        project_type: str = "commercial",
        hvhz: bool = True,
        flood_zone: bool = False
    ) -> Dict[str, Any]:
        """
        Start complete permitting workflow for a project

        This creates:
        - Code compliance checklists for all disciplines
        - Permit applications for specified types
        - Links to jurisdiction requirements

        Args:
            project_id: Project ID
            jurisdiction: Target jurisdiction name
            permit_types: Types of permits needed (default: building, electrical, mechanical, plumbing)
            project_type: Type of project
            hvhz: Is project in HVHZ
            flood_zone: Is project in flood zone

        Returns:
            Dictionary with all created resources
        """
        result = {
            "project_id": project_id,
            "jurisdiction": jurisdiction,
            "timestamp": datetime.now().isoformat(),
            "checklists": None,
            "permits": [],
            "jurisdiction_info": None
        }

        # Create checklists
        if self.compliance_db:
            result["checklists"] = self.create_project_checklists(
                project_id=project_id,
                project_type=project_type,
                hvhz=hvhz,
                flood_zone=flood_zone
            )

        # Get jurisdiction info
        if self.jurisdiction_db:
            result["jurisdiction_info"] = self.get_jurisdiction_info(jurisdiction)

        # Create permit applications
        if permit_types is None:
            permit_types = ["building", "electrical", "mechanical", "plumbing"]

        if self.permit_tracker:
            for permit_type in permit_types:
                try:
                    permit_id = self.create_permit_application(
                        project_id=project_id,
                        permit_type=permit_type,
                        jurisdiction=jurisdiction,
                        hvhz=hvhz
                    )
                    result["permits"].append({
                        "type": permit_type,
                        "id": permit_id,
                        "status": "created"
                    })
                except Exception as e:
                    result["permits"].append({
                        "type": permit_type,
                        "error": str(e)
                    })

        return result

    def get_dashboard(self) -> Dict[str, Any]:
        """Get project dashboard statistics"""
        stats = {
            "timestamp": datetime.now().isoformat(),
            "components": {
                "site_data_api": get_complete_site_data is not None,
                "project_database": self.project_db is not None,
                "report_generator": generate_site_report is not None,
                "zoning_database": self.zoning_db is not None,
                "code_compliance": self.compliance_db is not None,
                "permit_tracker": self.permit_tracker is not None,
                "jurisdiction_database": self.jurisdiction_db is not None,
                "comment_response": self.comment_system is not None,
                "noa_database": self.noa_db is not None,
                "fee_calculator": self.fee_calculator is not None,
                "pdf_generator": self.pdf_generator is not None,
                "revit_schedule_validator": self.schedule_validator is not None
            }
        }

        if self.project_db:
            stats["projects"] = self.project_db.get_dashboard_stats()

        if self.zoning_db:
            districts = self.zoning_db.get_all_districts()
            stats["zoning"] = {
                "total_districts": len(districts),
                "counties": list(set(d["county_name"] for d in districts))
            }

        if self.jurisdiction_db:
            jurisdictions = self.jurisdiction_db.get_all_jurisdictions()
            stats["jurisdictions"] = {
                "total": len(jurisdictions),
                "hvhz_jurisdictions": len(self.jurisdiction_db.get_hvhz_jurisdictions())
            }

        return stats

    def _generate_analysis_summary(self, analysis: Dict) -> Dict[str, Any]:
        """Generate a summary of the analysis"""
        summary = {
            "apis_successful": 0,
            "apis_failed": 0,
            "key_findings": [],
            "recommendations": []
        }

        site_data = analysis.get("site_data", {})

        # Count successes
        if analysis.get("site_data_success"):
            apis_used = site_data.get("apis_used", [])
            summary["apis_successful"] = len(apis_used)

        if analysis.get("zoning_success"):
            summary["apis_successful"] += 1

        # Extract key findings
        if site_data:
            # Flood zone
            flood = site_data.get("flood_zone", {})
            if flood.get("zone"):
                zone = flood["zone"]
                if zone.startswith("A") or zone.startswith("V"):
                    summary["key_findings"].append(f"Property is in flood zone {zone} - flood insurance required")
                else:
                    summary["key_findings"].append(f"Property is in flood zone {zone}")

            # Wind/HVHZ
            storm = site_data.get("storm_wind", {})
            if storm.get("hvhz"):
                summary["key_findings"].append("Property is in High-Velocity Hurricane Zone (HVHZ)")
                summary["recommendations"].append("Use Miami-Dade approved impact products")

            # Environmental
            env = site_data.get("environmental", {})
            env_summary = env.get("summary", {})
            if env_summary.get("risk_level") in ["MODERATE", "HIGH"]:
                summary["key_findings"].append(f"Environmental risk: {env_summary['risk_level']}")
                summary["recommendations"].append("Phase I ESA recommended")

            # Wetlands
            wetlands = env.get("wetlands", {})
            if wetlands.get("wetlands_nearby") == "LIKELY":
                summary["key_findings"].append("Wetlands likely present")
                summary["recommendations"].append("Wetland delineation study recommended")

            # Elevation
            elevation = site_data.get("elevation_ft")
            if elevation and elevation < 10:
                summary["key_findings"].append(f"Low elevation: {elevation:.1f} ft")

        # Zoning findings
        zoning = analysis.get("zoning", {})
        if zoning.get("found"):
            district = zoning.get("district", {})
            if district:
                summary["key_findings"].append(
                    f"Zoning: {district.get('district_code')} - {district.get('district_name')}"
                )
                if district.get("max_height_ft"):
                    summary["key_findings"].append(f"Max height: {district['max_height_ft']} ft")
                if district.get("max_density_units_acre"):
                    summary["key_findings"].append(f"Max density: {district['max_density_units_acre']} units/acre")

        return summary

    # =========================================================================
    # NEW MODULE METHODS
    # =========================================================================

    def search_noa_products(
        self,
        category: str = None,
        manufacturer: str = None,
        min_design_pressure: float = None
    ) -> List[Dict]:
        """Search NOA/Product Approval database"""
        if not self.noa_db:
            return []
        return self.noa_db.search_products(
            category=category,
            manufacturer=manufacturer,
            min_design_pressure=min_design_pressure
        )

    def calculate_permit_fees(
        self,
        jurisdiction: str,
        project_value: float,
        sqft: float = 0,
        **kwargs
    ) -> Dict[str, Any]:
        """Calculate permit fees for a jurisdiction"""
        if not self.fee_calculator:
            return {"error": "Fee calculator not available"}
        return self.fee_calculator.calculate_all_fees(
            jurisdiction=jurisdiction,
            project_value=project_value,
            sqft=sqft,
            **kwargs
        )

    def generate_fee_estimate(
        self,
        jurisdiction: str,
        project_value: float,
        sqft: float,
        project_name: str = "",
        **kwargs
    ) -> str:
        """Generate formatted fee estimate"""
        if not self.fee_calculator:
            return "Fee calculator not available"
        return self.fee_calculator.generate_fee_estimate(
            jurisdiction=jurisdiction,
            project_value=project_value,
            sqft=sqft,
            project_name=project_name,
            **kwargs
        )

    def generate_permit_application(
        self,
        jurisdiction: str,
        project_info: Dict[str, Any],
        owner_info: Dict[str, Any],
        contractor_info: Dict[str, Any],
        architect_info: Dict[str, Any] = None,
        output_path: str = None
    ) -> str:
        """Generate a permit application PDF"""
        if not self.pdf_generator or not ProjectInfo:
            return ""

        project = ProjectInfo(
            project_name=project_info.get('name', ''),
            project_address=project_info.get('address', ''),
            city=project_info.get('city', ''),
            state=project_info.get('state', 'FL'),
            zip_code=project_info.get('zip_code', ''),
            folio_number=project_info.get('folio_number', ''),
            occupancy_type=project_info.get('occupancy_type', ''),
            construction_type=project_info.get('construction_type', ''),
            stories=project_info.get('stories', 1),
            building_sqft=project_info.get('building_sqft', 0),
            lot_sqft=project_info.get('lot_sqft', 0),
            estimated_value=project_info.get('estimated_value', 0),
            scope_of_work=project_info.get('scope_of_work', ''),
            is_new_construction=project_info.get('is_new_construction', False),
            is_alteration=project_info.get('is_alteration', True)
        )

        owner = OwnerInfo(
            name=owner_info.get('name', ''),
            address=owner_info.get('address', ''),
            city=owner_info.get('city', ''),
            state=owner_info.get('state', 'FL'),
            zip_code=owner_info.get('zip_code', ''),
            phone=owner_info.get('phone', ''),
            email=owner_info.get('email', '')
        )

        contractor = ContractorInfo(
            company_name=contractor_info.get('company_name', ''),
            license_number=contractor_info.get('license_number', ''),
            qualifier_name=contractor_info.get('qualifier_name', ''),
            address=contractor_info.get('address', ''),
            city=contractor_info.get('city', ''),
            state=contractor_info.get('state', 'FL'),
            zip_code=contractor_info.get('zip_code', ''),
            phone=contractor_info.get('phone', ''),
            email=contractor_info.get('email', ''),
            insurance_company=contractor_info.get('insurance_company', ''),
            insurance_policy=contractor_info.get('insurance_policy', ''),
            insurance_expiration=contractor_info.get('insurance_expiration', '')
        )

        architect = None
        if architect_info and ArchitectInfo:
            architect = ArchitectInfo(
                name=architect_info.get('name', ''),
                company=architect_info.get('company', ''),
                license_number=architect_info.get('license_number', ''),
                address=architect_info.get('address', ''),
                city=architect_info.get('city', ''),
                state=architect_info.get('state', 'FL'),
                zip_code=architect_info.get('zip_code', ''),
                phone=architect_info.get('phone', ''),
                email=architect_info.get('email', '')
            )

        return self.pdf_generator.generate_building_permit_application(
            jurisdiction=jurisdiction,
            project=project,
            owner=owner,
            contractor=contractor,
            architect=architect,
            output_path=output_path
        )

    def validate_revit_schedules(
        self,
        doors: List[Dict] = None,
        windows: List[Dict] = None,
        walls: List[Dict] = None,
        rooms: List[Dict] = None,
        project_name: str = "",
        hvhz: bool = True
    ) -> Dict[str, Any]:
        """Validate Revit schedule data against code requirements"""
        if validate_revit_schedules:
            return validate_revit_schedules(
                project_name=project_name,
                hvhz=hvhz,
                doors=doors,
                windows=windows,
                walls=walls,
                rooms=rooms
            )
        return {"error": "Revit schedule validator not available"}


# Convenience functions for direct use
def analyze_site(address: str, **kwargs) -> Dict[str, Any]:
    """Quick site analysis"""
    si = SiteIntelligence()
    return si.analyze_site(address=address, **kwargs)


def create_project(address: str, project_name: str = None, **kwargs) -> Dict[str, Any]:
    """Create project with analysis"""
    si = SiteIntelligence()
    return si.create_project_with_analysis(address, project_name, **kwargs)


def lookup_zoning(county: str, district: str) -> Dict[str, Any]:
    """Quick zoning lookup"""
    si = SiteIntelligence()
    return si.lookup_zoning(county, district)


if __name__ == "__main__":
    print("=" * 70)
    print("SITE INTELLIGENCE - Unified Site Analysis System")
    print("=" * 70)

    # Initialize
    si = SiteIntelligence()

    # Show dashboard
    print("\nSystem Status:")
    dashboard = si.get_dashboard()
    for component, available in dashboard["components"].items():
        status = "OK" if available else "NOT AVAILABLE"
        print(f"  {component}: {status}")

    if dashboard.get("zoning"):
        print(f"\nZoning Database: {dashboard['zoning']['total_districts']} districts across {len(dashboard['zoning']['counties'])} counties")

    # Test quick zoning lookup
    print("\n" + "-" * 70)
    print("Quick Zoning Lookup: Miami-Dade RU-1")
    print("-" * 70)
    zoning = si.lookup_zoning("Miami-Dade", "RU-1")
    if zoning.get("found"):
        d = zoning["district"]
        print(f"  District: {d['district_code']} - {d['district_name']}")
        print(f"  Category: {d['category']}")
        print(f"  Max Height: {d['max_height_ft']} ft")
        print(f"  Max FAR: {d['max_far']}")
        print(f"  Max Density: {d['max_density_units_acre']} units/acre")

    # Test finding districts by criteria
    print("\n" + "-" * 70)
    print("Find Districts: Miami-Dade, 20+ units/acre")
    print("-" * 70)
    high_density = si.find_zoning_by_criteria(county="Miami-Dade", min_density=20)
    for d in high_density[:5]:
        print(f"  {d['district_code']}: {d['max_density_units_acre']} u/ac, {d['max_height_ft'] or 'No limit'} ft")

    # Test jurisdiction database
    if dashboard["components"].get("jurisdiction_database"):
        print("\n" + "-" * 70)
        print("Jurisdiction Database")
        print("-" * 70)
        jurisdictions = si.get_jurisdictions_by_county("Miami-Dade")
        print(f"  Miami-Dade jurisdictions: {len(jurisdictions)}")
        for j in jurisdictions[:3]:
            hvhz = "(HVHZ)" if j.get('hvhz') else ""
            print(f"    - {j['name']} {hvhz}")

    # Test permitting workflow demonstration
    if dashboard["components"].get("permit_tracker"):
        print("\n" + "-" * 70)
        print("Permitting Workflow Demo")
        print("-" * 70)
        print("  Starting permitting workflow for test project...")
        workflow = si.start_permitting_workflow(
            project_id=999,  # Test project
            jurisdiction="Miami-Dade County",
            permit_types=["building", "electrical"],
            project_type="commercial",
            hvhz=True
        )
        if workflow.get("checklists"):
            print(f"  Checklists created: {len(workflow['checklists'].get('checklists_created', []))}")
            print(f"  Total checklist items: {workflow['checklists'].get('total_items', 0)}")
        if workflow.get("permits"):
            print(f"  Permits created: {len([p for p in workflow['permits'] if 'id' in p])}")

    print("\n" + "=" * 70)
    print("System Ready for Site Analysis & Permitting")
    print("=" * 70)
    print("\nSite Analysis:")
    print("  si.analyze_site('11900 SW 216th St, Goulds, FL')")
    print("  si.create_project_with_analysis('123 Main St', 'My Project')")
    print("  si.lookup_zoning('Miami-Dade', 'RU-1')")
    print("\nPermit & Compliance:")
    print("  si.start_permitting_workflow(project_id, 'Miami-Dade County')")
    print("  si.create_project_checklists(project_id)")
    print("  si.get_jurisdiction_info('City of Miami')")
    print("  si.add_review_comments(project_id, comments)")
    print("  si.generate_response_letter(project_id, cycle_number=1)")
