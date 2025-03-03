"""
Data models for Operator Rounds Tracking.

This module defines the data models and structures used throughout the
application. Although SQLite doesn't enforce object-relational mapping,
these models provide a consistent interface for working with the application's
data entities.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime

@dataclass
class RoundItem:
    """Represents a single item within a section of a round."""
    description: str
    value: str = ""
    output: str = ""
    mode: str = ""
    id: Optional[int] = None
    section_id: Optional[int] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the item to a dictionary for JSON serialization."""
        return {
            "description": self.description,
            "value": self.value,
            "output": self.output,
            "mode": self.mode
        }

@dataclass
class Section:
    """Represents a section within a unit of a round."""
    unit: str
    section_name: str
    items: List[RoundItem] = field(default_factory=list)
    id: Optional[int] = None
    round_id: Optional[int] = None
    completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert the section to a dictionary for JSON serialization."""
        return {
            "unit": self.unit,
            "section_name": self.section_name,
            "completed": self.completed,
            "items": [item.to_dict() for item in self.items]
        }

    def add_item(self, description: str, value: str = "", output: str = "", mode: str = "") -> RoundItem:
        """Add a new item to this section and return it."""
        item = RoundItem(description=description, value=value, output=output, mode=mode)
        self.items.append(item)
        return item

    def get_item_by_description(self, description: str) -> Optional[RoundItem]:
        """Find an item by its description (case-insensitive)."""
        description_lower = description.lower().strip()
        for item in self.items:
            if item.description.lower().strip() == description_lower:
                return item
        return None

@dataclass
class Operator:
    """Represents an operator who conducts rounds."""
    name: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the operator to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

@dataclass
class Round:
    """Represents a complete round with all its sections and items."""
    round_type: str
    operator: Operator
    shift: str
    sections: List[Section] = field(default_factory=list)
    id: Optional[int] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the round to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "round_type": self.round_type,
            "operator": self.operator.to_dict(),
            "shift": self.shift,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "sections": [section.to_dict() for section in self.sections]
        }

    def add_section(self, unit: str, section_name: str) -> Section:
        """Add a new section to this round and return it."""
        section = Section(unit=unit, section_name=section_name)
        self.sections.append(section)
        return section

    def get_section_by_name(self, unit: str, section_name: str) -> Optional[Section]:
        """Find a section by its unit and name (case-insensitive)."""
        unit_lower = unit.lower().strip()
        section_name_lower = section_name.lower().strip()
        
        for section in self.sections:
            if (section.unit.lower().strip() == unit_lower and 
                section.section_name.lower().strip() == section_name_lower):
                return section
        return None

    def get_sections_by_unit(self, unit: str) -> List[Section]:
        """Get all sections for a specific unit."""
        unit_lower = unit.lower().strip()
        return [section for section in self.sections 
                if section.unit.lower().strip() == unit_lower]

    def get_units(self) -> List[str]:
        """Get a list of all unique units in this round."""
        return list(set(section.unit for section in self.sections))

@dataclass
class RoundTemplate:
    """Represents a template for creating new rounds with predefined sections and items."""
    name: str
    round_type: str
    sections: List[Dict[str, Any]] = field(default_factory=list)
    id: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the template to a dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "round_type": self.round_type,
            "sections": self.sections
        }

    def add_section_template(self, unit: str, section_name: str, items: List[Dict[str, str]] = None) -> None:
        """Add a section template to this round template."""
        self.sections.append({
            "unit": unit,
            "section_name": section_name,
            "items": items or []
        })