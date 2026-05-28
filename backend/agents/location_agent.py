"""
Location Intelligence & Hospital Finder Agent

Detects location-based queries and routes to hospital/clinic/pharmacy search.
Handles pincodes, city names, coordinates, and WhatsApp live locations.
"""

import asyncio
import re
from typing import Dict, Optional, Tuple

from tools.hospital_search_tool import (
    search_facilities_near_location,
    search_nearby_ambulances,
)
from services.maps_service import MapsService
from config.logger import logger


class LocationAgent:
    """
    Detects location queries and searches for nearby medical facilities.

    Handles:
    - "hospital near me"
    - "700137 hospital"
    - "find clinics in Kolkata"
    - "ambulance emergency"
    - WhatsApp live locations (lat/lon)
    """

    def __init__(self):
        self.name = "LocationAgent"
        self.maps_service = MapsService()

    # INTENT DETECTION

    def _detect_location_intent(self, query: str) -> Dict:
        """
        Detect location-related intents from query.

        Returns:
            {
                "is_location_query": bool,
                "intent_type": "hospital" | "clinic" | "pharmacy" | "ambulance" | "general",
                "is_emergency": bool,
                "facility_types": List[str]
            }
        """
        query_lower = query.lower()

        # Emergency keywords
        emergency_keywords = [
            "emergency", "urgent", "ambulance", "911", "critical",
            "severe", "accident", "emergency nearby", "help"
        ]
        is_emergency = any(
            keyword in query_lower
            for keyword in emergency_keywords
        )

        # Facility type detection
        hospital_keywords = [
            "hospital", "medical center", "medical", "doctor",
            "nursing home", "nursing home near",
        ]
        clinic_keywords = ["clinic", "medical clinic", "private clinic"]
        pharmacy_keywords = ["pharmacy", "chemist", "medicine"]
        ambulance_keywords = ["ambulance", "emergency vehicle"]

        is_hospital = any(
            keyword in query_lower
            for keyword in hospital_keywords
        )
        is_clinic = any(
            keyword in query_lower
            for keyword in clinic_keywords
        )
        is_pharmacy = any(
            keyword in query_lower
            for keyword in pharmacy_keywords
        )
        is_ambulance = (
            any(keyword in query_lower for keyword in ambulance_keywords)
            or is_emergency
        )

        # Location/proximity keywords
        proximity_keywords = [
            "near me", "nearby", "close", "near", "around",
            "within", "find", "search", "locate"
        ]
        is_proximity = any(
            keyword in query_lower
            for keyword in proximity_keywords
        )

        # Determine if it's a location query
        is_location_query = (
            is_proximity or is_hospital or is_clinic or
            is_pharmacy or is_ambulance
        )

        # Extract facility types
        facility_types = []
        if is_hospital:
            facility_types.append("hospitals")
        if is_clinic:
            facility_types.append("clinics")
        if is_pharmacy:
            facility_types.append("pharmacies")
        if is_ambulance or is_emergency:
            facility_types.append("ambulances")

        if not facility_types:
            facility_types = ["hospitals", "clinics"]

        # Determine intent type
        if is_ambulance or is_emergency:
            intent_type = "ambulance"
        elif is_hospital:
            intent_type = "hospital"
        elif is_clinic:
            intent_type = "clinic"
        elif is_pharmacy:
            intent_type = "pharmacy"
        else:
            intent_type = "general"

        return {
            "is_location_query": is_location_query,
            "intent_type": intent_type,
            "is_emergency": is_emergency,
            "facility_types": facility_types,
        }
    
    # LOCATION EXTRACTION

    def _extract_place_name(self, query: str) -> Optional[str]:
        """Extract a place name from a free-form location query."""
        query_lower = query.lower()

        patterns = [
            r"(?:in|at|near|around|on)\s+([a-z0-9\s]+?)(?:\s+location|\s+nearby|\s+hospital|\s+clinic|\s+pharmacy|\s+ambulance|\s+link|$)",
            r"([a-z0-9\s]+?)\s+location$",
        ]

        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                place = match.group(1).strip()
                place = re.sub(
                    r"\b(give me|please|some|find|nearby|hospital|clinic|pharmacy|ambulance|link)\b",
                    "",
                    place,
                ).strip()
                place = re.sub(r"\s+", " ", place)
                if place:
                    return place

        return None

    async def _extract_location(
        self,
        query: str,
        user_pincode: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Optional[Tuple[float, float]]:
        """
        Extract location from query or use provided coordinates.

        Priority:
        1. WhatsApp live location (lat/lon)
        2. Pincode in query
        3. City in query
        4. Free-form location phrase
        5. User's registered pincode
        6. Fail
        """
        try:
            # Use WhatsApp location if provided
            if latitude and longitude:
                logger.info(
                    f"[{self.name}] Using WhatsApp location "
                    f"({latitude}, {longitude})"
                )
                return (latitude, longitude)

            # Extract pincode from query
            pincode = self.maps_service.extract_pincode(query)
            if pincode:
                logger.info(f"[{self.name}] Found pincode in query: {pincode}")
                coords = (
                    await self.maps_service.get_coordinates_from_pincode(
                        pincode
                    )
                )
                if coords:
                    return coords

            # Extract city from query
            city_data = self.maps_service.extract_city_district(query)
            if city_data.get("city"):
                logger.info(
                    f"[{self.name}] Found city in query: {city_data['city']}"
                )
                coords = (
                    await self.maps_service.get_coordinates_from_city(
                        city_data["city"]
                    )
                )
                if coords:
                    return coords

            # Try extracting an explicit place name before geocoding
            place_name = self._extract_place_name(query)
            if place_name:
                logger.info(
                    f"[{self.name}] Extracted place name: {place_name}"
                )
                coords = (
                    await self.maps_service.get_coordinates_from_query(
                        place_name
                    )
                )
                if coords:
                    return coords

            # Try geocoding the full query text for free-form location names
            coords = (
                await self.maps_service.get_coordinates_from_query(query)
            )
            if coords:
                return coords

            # Fall back to user's registered pincode
            if user_pincode:
                logger.info(
                    f"[{self.name}] Using user's pincode: {user_pincode}"
                )
                coords = (
                    await self.maps_service.get_coordinates_from_pincode(
                        user_pincode
                    )
                )
                if coords:
                    return coords

            logger.warning(f"[{self.name}] Could not extract location")
            return None

        except Exception as e:
            logger.error(f"[{self.name}] Location extraction error: {e}")
            return None

    # MAIN ANALYSIS METHOD


    async def analyze(
        self,
        query: str,
        phone_number: str,
        user_name: str = "User",
        pincode: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        conversation_history: list = None,
        medical_context: str = "",
        long_term_memory: str = "",
        **kwargs
    ) -> Dict:
        """
        Analyze location query and search for nearby facilities.

        Args:
            query: User's query text
            phone_number: User's phone number
            user_name: User's name
            pincode: User's registered pincode
            latitude: WhatsApp location latitude (optional)
            longitude: WhatsApp location longitude (optional)
            conversation_history: Chat history
            medical_context: Medical profile context
            long_term_memory: Long-term memory of user

        Returns:
            {
                "success": bool,
                "intent": str,
                "is_emergency": bool,
                "location": dict,
                "facilities": dict,
                "message": str,
                "full_response": str
            }
        """
        logger.info(
            f"[{self.name}] Analyzing location query: {query[:60]}"
        )

        try:
            # 1. Detect intent
            intent_data = self._detect_location_intent(query)
            if not intent_data["is_location_query"]:
                return {
                    "success": False,
                    "message": "Not a location query",
                    "is_location_query": False,
                }

            logger.info(
                f"[{self.name}] Detected intent: "
                f"{intent_data['intent_type']} "
                f"(emergency={intent_data['is_emergency']})"
            )

            # 2. Extract location
            coords = await self._extract_location(
                query=query,
                user_pincode=pincode,
                latitude=latitude,
                longitude=longitude,
            )

            if not coords:
                return {
                    "success": False,
                    "message": (
                        "Could not determine location. "
                        "Please provide pincode or city name."
                    ),
                }

            latitude_resolved, longitude_resolved = coords
            logger.info(
                f"[{self.name}] Resolved location: "
                f"({latitude_resolved}, {longitude_resolved})"
            )

            # 3. Reverse geocode to get address
            address_data = (
                await self.maps_service.reverse_geocode(
                    latitude_resolved, longitude_resolved
                )
            )
            address_str = (
                address_data["address"]
                if address_data
                else "Unknown location"
            )

            # 4. Search facilities
            logger.info(
                f"[{self.name}] Searching for: "
                f"{intent_data['facility_types']}"
            )

            # Emergency: prioritize ambulances
            if intent_data["is_emergency"]:
                facilities_result = (
                    await search_nearby_ambulances(
                        latitude_resolved,
                        longitude_resolved,
                        radius_meters=5000,
                        limit=5,
                    )
                )
            else:
                facilities_result = (
                        await search_facilities_near_location(
                            latitude_resolved,
                            longitude_resolved,
                            facility_types=intent_data["facility_types"],
                            radius_meters=5000,
                        )
                    )

            # 5. Format response
            # The search tool returns a wrapper {success, location, facilities, message}
            # The formatter expects the inner mapping of facility type -> results, so extract it.
            facilities_map = facilities_result.get("facilities") if isinstance(facilities_result, dict) else facilities_result

            response_msg = self._format_response(
                query=query,
                location_address=address_str,
                intent=intent_data,
                facilities=facilities_map,
            )

            return {
                "success": facilities_result.get("success", False),
                "intent": intent_data["intent_type"],
                "is_emergency": intent_data["is_emergency"],
                "location": {
                    "latitude": latitude_resolved,
                    "longitude": longitude_resolved,
                    "address": address_str,
                },
                "facilities": facilities_result,
                "message": response_msg,
                "full_response": response_msg,
            }

        except Exception as e:
            logger.error(
                f"[{self.name}] Analysis error: {e}",
                exc_info=True
            )
            return {
                "success": False,
                "message": f"Error processing location query: {str(e)}",
            }
        
    # RESPONSE FORMATTING

    def _format_response(
        self,
        query: str,
        location_address: str,
        intent: Dict,
        facilities: Dict,
    ) -> str:
        """Format search results into a user-friendly message."""
        try:
            lines = []

            if intent["is_emergency"]:
                lines.append("🚨 *EMERGENCY MODE*\n")
                lines.append(
                    f"🏥 *Nearby Ambulances & Emergency Services*\n"
                )
            else:
                intent_type = intent["intent_type"]
                if intent_type == "hospital":
                    lines.append("🏥 *Nearby Hospitals*\n")
                elif intent_type == "clinic":
                    lines.append("🏥 *Nearby Clinics*\n")
                elif intent_type == "pharmacy":
                    lines.append("💊 *Nearby Pharmacies*\n")
                else:
                    lines.append("📍 *Nearby Medical Facilities*\n")

            lines.append(f"📍 *Location:* {location_address}\n")
            
            # Check if search was successful and returned results
            has_results = False
            for facility_type in intent["facility_types"]:
                if facility_type in facilities:
                    facility_list = facilities[facility_type].get(facility_type, [])
                    if facility_list:
                        has_results = True
                        break
            
            if intent["is_emergency"] and "ambulances" in facilities:
                ambulances = facilities["ambulances"].get("ambulances", [])
                if ambulances:
                    has_results = True

            # Format facilities or show fallback
            if intent["is_emergency"] and "ambulances" in facilities:
                ambulances = facilities["ambulances"].get(
                    "ambulances", []
                )
                if ambulances:
                    lines.append("*Ambulances:*")
                    for i, amb in enumerate(ambulances[:5], 1):
                        phone = amb.get("phone", "Not available")
                        dist = amb.get("distance_km", 0)
                        lines.append(
                            f"{i}. {amb['name']} "
                            f"({dist} km)\n"
                            f"   📞 {phone}\n"
                            f"   🗺 {amb.get('address', '')}\n"
                            f"   🔗 {amb.get('maps_url', '')}"
                        )
                else:
                    lines.append(
                        "❌ No ambulances found in our database.\n\n"
                        "🚨 *EMERGENCY - Call immediately:*\n"
                        "📞 100 - Police Emergency\n"
                        "📞 102 - Ambulance (India)\n"
                        "📞 1298 - Disaster Management\n\n"
                        "📍 Or search on Google Maps for nearest ambulance services."
                    )
            elif has_results:
                for facility_type in intent["facility_types"]:
                    if facility_type in facilities:
                        facility_data = facilities[facility_type]
                        fac_list = facility_data.get(
                            facility_type, []
                        )
                        if fac_list:
                            lines.append(
                                f"\n*{facility_type.capitalize()}:*"
                            )
                            for i, fac in enumerate(fac_list[:5], 1):
                                phone = fac.get("phone", "Not available")
                                dist = fac.get("distance_km", 0)
                                lines.append(
                                    f"{i}. {fac['name']} "
                                    f"({dist} km)\n"
                                    f"   📞 {phone}\n"
                                    f"   🗺 {fac.get('address', '')}\n"
                                    f"   🔗 {fac.get('maps_url', '')}"
                                )
                lines.append(
                    "\n✅ Use the map links to navigate to the facility."
                )
            else:
                # Fallback when no results found
                facility_type = intent["intent_type"] or "medical"
                lines.append(
                    f"❌ No {facility_type}s found in our database for this location.\n\n"
                    f"📍 *Alternative ways to find {facility_type}s:*\n"
                    f"1️⃣ Use *Google Maps* search\n"
                    f"2️⃣ Call your local health authority\n"
                    f"3️⃣ Check hospital websites for directions\n\n"
                    f"📍 *Location searched:* {location_address}\n"
                    f"💡 Try searching with a different location or nearby area."
                )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"[{self.name}] Response format error: {e}")
            return "Found nearby facilities. Please view the details above."
