"""
Maps & Location Service

Provides geolocation, reverse geocoding, and hospital search
using free APIs: geopy, Overpass API, OpenStreetMap.
"""

import asyncio
import json
from typing import Optional, List, Dict, Tuple
from urllib.parse import quote_plus
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import requests
import re

from config.logger import logger


class MapsService:
    """Service for location intelligence and hospital search."""

    def __init__(self):
        self.geocoder = Nominatim(user_agent="arogyaai_maps_service")
        # Using single most reliable mirror (others have 403/timeout issues)
        self.overpass_urls = [
            "https://overpass-api.de/api/interpreter",
        ]
        self.nominatim_search_url = "https://nominatim.openstreetmap.org/search"

    async def _run_overpass_query(self, query: str):
        """Run an Overpass QL query against available mirrors."""
        headers = {
            "User-Agent": "ArogyaAI/1.0",
            "Accept": "application/json",
        }

        for url in self.overpass_urls:
            try:
                logger.info(f"[MapsService] Overpass URL: {url}")
                response = await asyncio.to_thread(
                    requests.post,
                    url,
                    data={"data": query},
                    headers=headers,
                    timeout=60,
                )
                if response.status_code == 200:
                    return response

                logger.warning(
                    f"[MapsService] Overpass API error from {url}: "
                    f"{response.status_code} - {response.text.strip()}"
                )
            except Exception as e:
                logger.warning(
                    f"[MapsService] Overpass request failed for {url}: {e}"
                )

        return None

    def build_google_maps_url(
        self,
        name: str,
        latitude: float,
        longitude: float
    ) -> str:
        """Build a Google Maps search link using name and coordinates."""
        query = f"{name} {latitude},{longitude}" if name else f"{latitude},{longitude}"
        return (
            "https://www.google.com/maps/search/?api=1&query="
            f"{quote_plus(query)}"
        )

 
    # PINCODE & LOCATION EXTRACTION

    def extract_pincode(self, text: str) -> Optional[str]:
        """Extract pincode from text. Supports Indian pincodes (6 digits)."""
        match = re.search(r'\b[0-9]{6}\b', text)
        return match.group(0) if match else None

    def extract_city_district(self, text: str) -> Dict[str, str]:
        """Extract city/district mentions from text."""
        # Simple keyword extraction - can be enhanced with NER
        cities_keywords = {
            "kolkata": ["kolkata", "calcutta", "kal", "ccw"],
            "delhi": ["delhi", "new delhi", "noida"],
            "mumbai": ["mumbai", "bombay"],
            "bangalore": ["bangalore", "bengaluru"],
            "hyderabad": ["hyderabad", "hyd"],
            "pune": ["pune", "poona"],
            "ahmedabad": ["ahmedabad", "amd"],
            "budge budge": ["budge budge", "budgebudge"],
        }

        text_lower = text.lower()
        detected = {"city": None, "district": None}

        for city, keywords in cities_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected["city"] = city
                    break

        return detected

    # GEOLOCATION FROM PINCODE/CITY

    async def get_coordinates_from_pincode(
        self,
        pincode: str
    ) -> Optional[Tuple[float, float]]:
        """
        Get lat/lon from Indian pincode.
        Uses Nominatim (OpenStreetMap).
        """
        try:
            logger.info(f"[MapsService] Resolving pincode: {pincode}")
            location = await asyncio.to_thread(
                self.geocoder.geocode,
                f"{pincode} India"
            )

            if location:
                logger.info(
                    f"[MapsService] Pincode {pincode} -> "
                    f"({location.latitude}, {location.longitude})"
                )
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"[MapsService] Pincode {pincode} not found")
                return None

        except Exception as e:
            logger.error(f"[MapsService] Geocode error: {e}")
            return None

    async def get_coordinates_from_city(
        self,
        city: str
    ) -> Optional[Tuple[float, float]]:
        """Get lat/lon from city name."""
        try:
            logger.info(f"[MapsService] Resolving city: {city}")
            location = await asyncio.to_thread(
                self.geocoder.geocode,
                f"{city} India"
            )

            if location:
                logger.info(
                    f"[MapsService] City {city} -> "
                    f"({location.latitude}, {location.longitude})"
                )
                return (location.latitude, location.longitude)
            else:
                logger.warning(f"[MapsService] City {city} not found")
                return None

        except Exception as e:
            logger.error(f"[MapsService] Geocode error: {e}")
            return None

    async def get_coordinates_from_query(
        self,
        query: str
    ) -> Optional[Tuple[float, float]]:
        """Geocode a full text query to resolve a location."""
        try:
            logger.info(
                f"[MapsService] Resolving freeform location query: {query}"
            )
            # Try geocoding in multiple ways: raw query, query + country, and Nominatim HTTP search
            # 1) Raw query
            location = await asyncio.to_thread(self.geocoder.geocode, query)
            if not location:
                # 2) Query with country hint
                location = await asyncio.to_thread(self.geocoder.geocode, f"{query} India")

            if location:
                logger.info(
                    f"[MapsService] Query resolved -> "
                    f"({location.latitude}, {location.longitude})"
                )
                return (location.latitude, location.longitude)

            # 3) Fallback to Nominatim HTTP search (more forgiving)
            try:
                params = {"q": query, "format": "json", "limit": 1}
                headers = {"User-Agent": "ArogyaAI/1.0", "Accept": "application/json"}
                resp = await asyncio.to_thread(requests.get, self.nominatim_search_url, params=params, headers=headers, timeout=15)
                if resp.status_code == 200:
                    items = resp.json()
                    if items:
                        loc = items[0]
                        lat = float(loc.get("lat", 0))
                        lon = float(loc.get("lon", 0))
                        logger.info(f"[MapsService] Nominatim HTTP resolved -> ({lat}, {lon})")
                        return (lat, lon)
            except Exception:
                pass

            # 4) Try Overpass name search as a last-resort for small/local place names
            try:
                name_query = (
                    f"[out:json][timeout:25];"
                    f"(node[\"name\"~\"{re.escape(query)}\",i];"
                    f"way[\"name\"~\"{re.escape(query)}\",i];"
                    f"relation[\"name\"~\"{re.escape(query)}\",i];);")
                name_query += "out center;"
                resp = await self._run_overpass_query(name_query)
                if resp and resp.status_code == 200:
                    data = resp.json()
                    elems = data.get("elements", [])
                    if elems:
                        elem = elems[0]
                        center = elem.get("center") or {"lat": elem.get("lat"), "lon": elem.get("lon")}
                        if center and center.get("lat") and center.get("lon"):
                            lat = float(center["lat"])
                            lon = float(center["lon"])
                            logger.info(f"[MapsService] Overpass name resolved -> ({lat}, {lon})")
                            return (lat, lon)
            except Exception:
                pass

            logger.warning(f"[MapsService] Freeform query not resolved: {query}")
            return None

        except Exception as e:
            logger.error(f"[MapsService] Geocode error: {e}")
            return None

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Dict]:
        """Reverse geocode to get address from coordinates."""
        try:
            logger.info(
                f"[MapsService] Reverse geocoding "
                f"({latitude}, {longitude})"
            )
            location = await asyncio.to_thread(
                self.geocoder.reverse,
                f"{latitude}, {longitude}"
            )

            if location:
                return {
                    "address": location.address,
                    "latitude": latitude,
                    "longitude": longitude,
                }
            return None

        except Exception as e:
            logger.error(f"[MapsService] Reverse geocode error: {e}")
            return None
        
    # HOSPITAL SEARCH (Overpass API + Nominatim)

    async def search_hospitals_overpass(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 5000,
        amenity_type: str = "hospital"
    ) -> List[Dict]:
        """
        Search for hospitals/clinics using Overpass API.
        Returns up to 50 results.
        """
        try:
            logger.info(
                f"[MapsService] Searching {amenity_type}s "
                f"near ({latitude}, {longitude}) "
                f"radius={radius_m}m"
            )

            # Build Overpass QL query using around() to improve nearby search coverage
            if amenity_type == "hospital":
                query_tags = [
                    "node[amenity=hospital]",
                    "way[amenity=hospital]",
                    "relation[amenity=hospital]",
                    "node[healthcare=hospital]",
                    "way[healthcare=hospital]",
                    "relation[healthcare=hospital]",
                    "node[healthcare=nursing_home]",
                    "way[healthcare=nursing_home]",
                    "relation[healthcare=nursing_home]",
                ]
            elif amenity_type == "clinic":
                query_tags = [
                    "node[amenity=clinic]",
                    "way[amenity=clinic]",
                    "relation[amenity=clinic]",
                    "node[healthcare=clinic]",
                    "way[healthcare=clinic]",
                    "relation[healthcare=clinic]",
                ]
            else:
                query_tags = [
                    f"node[amenity={amenity_type}]",
                    f"way[amenity={amenity_type}]",
                    f"relation[amenity={amenity_type}]",
                ]

            query_parts = []
            for tag in query_tags:
                query_parts.append(
                    f"{tag}(around:{radius_m},{latitude},{longitude});"
                )

            overpass_query = (
                f"[out:json][timeout:25];"
                f"({''.join(query_parts)});"
                f"out center;"
            )

            response = await self._run_overpass_query(overpass_query)
            if response is None:
                logger.warning(
                    "[MapsService] Overpass API failed on all mirrors"
                )
                return []

            data = response.json()
            elements = data.get("elements", [])

            results = []
            for elem in elements:
                tags = elem.get("tags", {})
                location = None
                if "lat" in elem and "lon" in elem:
                    location = {"lat": elem["lat"], "lon": elem["lon"]}
                elif "center" in elem:
                    location = elem["center"]

                if not location:
                    continue

                address = tags.get("addr:full", "")
                if not address:
                    address_parts = [
                        tags.get("addr:street", ""),
                        tags.get("addr:suburb", ""),
                        tags.get("addr:city", ""),
                        tags.get("addr:postcode", ""),
                    ]
                    address = ", ".join(
                        part for part in address_parts if part
                    )

                results.append({
                    "name": tags.get("name")
                    or tags.get("operator")
                    or tags.get("official_name")
                    or "Unknown",
                    "latitude": location["lat"],
                    "longitude": location["lon"],
                    "address": address,
                    "phone": tags.get("phone", "")
                    or tags.get("contact:phone", ""),
                    "website": tags.get("website", ""),
                    "opening_hours": tags.get(
                        "opening_hours", "Unknown"
                    ),
                })

            logger.info(
                f"[MapsService] Found {len(results)} "
                f"{amenity_type}s via Overpass"
            )
            return results

        except Exception as e:
            logger.error(
                f"[MapsService] Overpass search error: {e}"
            )
            return []

    async def search_nominatim_facilities(
        self,
        query: str,
        latitude: float,
        longitude: float,
        radius_m: int = 10000,
        limit: int = 10,
    ) -> List[Dict]:
        """Search Nominatim for facilities as a fallback."""
        try:
            logger.info(
                f"[MapsService] Searching Nominatim for '{query}' "
                f"near ({latitude}, {longitude}) "
                f"radius={radius_m}m"
            )

            bbox_delta = radius_m / 111000
            viewbox = (
                f"{longitude - bbox_delta},"
                f"{latitude + bbox_delta},"
                f"{longitude + bbox_delta},"
                f"{latitude - bbox_delta}"
            )

            params = {
                "q": query,
                "format": "json",
                "limit": limit,
                "addressdetails": 1,
                "viewbox": viewbox,
                "bounded": 1,
            }
            headers = {
                "User-Agent": "ArogyaAI/1.0",
                "Accept": "application/json",
            }

            response = await asyncio.to_thread(
                requests.get,
                self.nominatim_search_url,
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code != 200:
                logger.warning(
                    f"[MapsService] Nominatim failed: "
                    f"{response.status_code} - {response.text.strip()}"
                )
                return []

            locations = response.json()
            results = []
            for loc in locations:
                name = loc.get("display_name", "Unknown")
                if "," in name:
                    name = name.split(",")[0].strip()

                results.append({
                    "name": name,
                    "latitude": float(loc.get("lat", 0)),
                    "longitude": float(loc.get("lon", 0)),
                    "address": loc.get("display_name", ""),
                    "phone": "",
                    "website": "",
                    "opening_hours": "",
                })

            logger.info(
                f"[MapsService] Found {len(results)} "
                f"{query} facilities via Nominatim"
            )
            return results

        except Exception as e:
            logger.error(f"[MapsService] Nominatim search error: {e}")
            return []

    async def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """Calculate distance in km between two coordinates."""
        try:
            point1 = (lat1, lon1)
            point2 = (lat2, lon2)
            distance_km = geodesic(point1, point2).kilometers
            return round(distance_km, 2)
        except Exception as e:
            logger.error(f"[MapsService] Distance calc error: {e}")
            return 0.0

    async def search_hospitals(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 10000,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search for hospitals with distance calculation.
        Returns sorted list by distance.
        """
        hospitals = await self.search_hospitals_overpass(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            amenity_type="hospital",
        )

        if len(hospitals) < limit:
            nominatim_hospitals = await self.search_nominatim_facilities(
                "hospital",
                latitude,
                longitude,
                radius_m=radius_m,
                limit=limit,
            )
            nominatim_nursing = await self.search_nominatim_facilities(
                "nursing home",
                latitude,
                longitude,
                radius_m=radius_m,
                limit=limit,
            )

            combined = hospitals + nominatim_hospitals + nominatim_nursing
            unique = {}
            for entry in combined:
                key = (
                    entry.get("name", "").lower(),
                    round(entry.get("latitude", 0), 6),
                    round(entry.get("longitude", 0), 6),
                )
                if key not in unique:
                    unique[key] = entry
            hospitals = list(unique.values())

        # Calculate distances and sort
        for hospital in hospitals:
            distance = await self.calculate_distance(
                latitude,
                longitude,
                hospital["latitude"],
                hospital["longitude"],
            )
            hospital["distance_km"] = distance
            hospital["maps_url"] = self.build_google_maps_url(
                hospital.get("name", ""),
                hospital["latitude"],
                hospital["longitude"],
            )

        # Sort by distance
        hospitals.sort(key=lambda h: h["distance_km"])

        logger.info(f"[MapsService] Returning {len(hospitals[:limit])} hospitals")
        return hospitals[:limit]

    async def search_ambulances(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 5000,
        limit: int = 10,
    ) -> List[Dict]:
        """Search for ambulance services."""
        try:
            logger.info(
                f"[MapsService] Searching ambulances "
                f"near ({latitude}, {longitude})"
            )

            bbox_delta = radius_m / 111000
            bbox = (
                f"{latitude - bbox_delta},"
                f"{longitude - bbox_delta},"
                f"{latitude + bbox_delta},"
                f"{longitude + bbox_delta}"
            )

            # Simplified Overpass query for ambulance search
            overpass_query = (
                f"[out:json][timeout:10];"
                f"(node[emergency=ambulance_station]({bbox});node[amenity=ambulance]({bbox}););out center;"
            )

            response = await self._run_overpass_query(overpass_query)
            if response is None:
                logger.warning(
                    "[MapsService] Overpass API failed on all mirrors"
                )
                return []

            data = response.json()
            elements = data.get("elements", [])

            results = []
            for elem in elements:
                if "center" in elem:
                    center = elem["center"]
                    tags = elem.get("tags", {})
                    distance = await self.calculate_distance(
                        latitude, longitude,
                        center["lat"], center["lon"]
                    )
                    results.append({
                        "name": tags.get(
                            "name", "Ambulance Service"
                        ),
                        "latitude": center["lat"],
                        "longitude": center["lon"],
                        "phone": tags.get("phone", ""),
                        "distance_km": distance,
                        "address": tags.get("addr:full", ""),
                    })

            results.sort(key=lambda a: a["distance_km"])
            return results[:limit]

        except Exception as e:
            logger.error(f"[MapsService] Ambulance search error: {e}")
            return []

    async def search_clinics(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 5000,
        limit: int = 10,
    ) -> List[Dict]:
        """Search for private clinics."""
        clinics = await self.search_hospitals_overpass(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_m,
            amenity_type="clinic",
        )

        for clinic in clinics:
            distance = await self.calculate_distance(
                latitude, longitude,
                clinic["latitude"], clinic["longitude"]
            )
            clinic["distance_km"] = distance

        clinics.sort(key=lambda c: c["distance_km"])
        return clinics[:limit]

    async def search_pharmacies(
        self,
        latitude: float,
        longitude: float,
        radius_m: int = 5000,
        limit: int = 10,
    ) -> List[Dict]:
        """Search for pharmacies."""
        try:
            bbox_delta = radius_m / 111000
            bbox = (
                f"{latitude - bbox_delta},"
                f"{longitude - bbox_delta},"
                f"{latitude + bbox_delta},"
                f"{longitude + bbox_delta}"
            )

            # Simplified Overpass query for pharmacy search
            overpass_query = (
                f"[out:json][timeout:10];"
                f"(node[amenity=pharmacy]({bbox});way[amenity=pharmacy]({bbox}););out center;"
            )

            response = await self._run_overpass_query(overpass_query)
            if response is None:
                logger.warning(
                    "[MapsService] Overpass API failed on all mirrors"
                )
                return []

            data = response.json()
            elements = data.get("elements", [])

            results = []
            for elem in elements:
                if "center" in elem:
                    center = elem["center"]
                    tags = elem.get("tags", {})
                    distance = await self.calculate_distance(
                        latitude, longitude,
                        center["lat"], center["lon"]
                    )
                    results.append({
                        "name": tags.get("name", "Pharmacy"),
                        "latitude": center["lat"],
                        "longitude": center["lon"],
                        "address": tags.get("addr:full", ""),
                        "phone": tags.get("phone", ""),
                        "distance_km": distance,
                    })

            results.sort(key=lambda p: p["distance_km"])
            return results[:limit]

        except Exception as e:
            logger.error(f"[MapsService] Pharmacy search error: {e}")
            return []
