"""
Hospital Search Tool

Provides structured hospital/clinic/pharmacy/ambulance search functionality
for the location agent.
"""

import asyncio
from typing import Dict, List, Optional
import json

from services.maps_service import MapsService
from config.logger import logger


# ══════════════════════════════════════════════════════
# GLOBAL MAPS SERVICE
# ══════════════════════════════════════════════════════

_maps_service = None


def _get_maps_service() -> MapsService:
    """Lazy load maps service."""
    global _maps_service
    if _maps_service is None:
        _maps_service = MapsService()
    return _maps_service


# ══════════════════════════════════════════════════════
# HOSPITAL SEARCH
# ══════════════════════════════════════════════════════

async def search_nearby_hospitals(
    latitude: float,
    longitude: float,
    radius_meters: int = 10000,
    limit: int = 10,
) -> dict:
    """
    Find nearby hospitals.

    Args:
        latitude: Location latitude
        longitude: Location longitude
        radius_meters: Search radius in meters
        limit: Max results to return

    Returns:
        {
            "success": bool,
            "hospitals": [
                {
                    "name": str,
                    "address": str,
                    "distance_km": float,
                    "phone": str,
                    "website": str,
                    "opening_hours": str,
                    "latitude": float,
                    "longitude": float,
                    "maps_url": str
                }
            ],
            "total_found": int,
            "message": str
        }
    """
    try:
        logger.info(
            f"[HospitalSearchTool] Finding hospitals "
            f"near ({latitude}, {longitude})"
        )

        maps_service = _get_maps_service()
        hospitals = await maps_service.search_hospitals(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_meters,
            limit=limit,
        )

        # Format response
        formatted_hospitals = []
        for hospital in hospitals:
            maps_url = hospital.get("maps_url")
            if not maps_url:
                maps_url = _get_maps_service().build_google_maps_url(
                    hospital.get("name", ""),
                    hospital.get("latitude", 0),
                    hospital.get("longitude", 0),
                )
            formatted_hospitals.append({
                "name": hospital.get("name", "Unknown Hospital"),
                "address": hospital.get("address", ""),
                "distance_km": hospital.get("distance_km", 0),
                "phone": hospital.get("phone", "Not available"),
                "website": hospital.get("website", ""),
                "opening_hours": hospital.get("opening_hours", ""),
                "latitude": hospital.get("latitude", 0),
                "longitude": hospital.get("longitude", 0),
                "maps_url": maps_url,
            })

        return {
            "success": True,
            "hospitals": formatted_hospitals,
            "total_found": len(formatted_hospitals),
            "message": (
                f"Found {len(formatted_hospitals)} hospitals "
                f"within {radius_meters}m"
            ),
        }

    except Exception as e:
        logger.error(f"[HospitalSearchTool] Error: {e}")
        return {
            "success": False,
            "hospitals": [],
            "total_found": 0,
            "message": f"Error searching hospitals: {str(e)}",
        }


# ══════════════════════════════════════════════════════
# AMBULANCE SEARCH
# ══════════════════════════════════════════════════════

async def search_nearby_ambulances(
    latitude: float,
    longitude: float,
    radius_meters: int = 5000,
    limit: int = 5,
) -> dict:
    """Find nearby ambulance services (emergency)."""
    try:
        logger.info(
            f"[HospitalSearchTool] Finding ambulances "
            f"near ({latitude}, {longitude})"
        )

        maps_service = _get_maps_service()
        ambulances = await maps_service.search_ambulances(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_meters,
            limit=limit,
        )

        formatted_ambulances = []
        for ambulance in ambulances:
            maps_url = ambulance.get("maps_url")
            if not maps_url:
                maps_url = _get_maps_service().build_google_maps_url(
                    ambulance.get("name", ""),
                    ambulance.get("latitude", 0),
                    ambulance.get("longitude", 0),
                )
            formatted_ambulances.append({
                "name": ambulance.get("name", "Ambulance"),
                "distance_km": ambulance.get("distance_km", 0),
                "phone": ambulance.get("phone", "Not available"),
                "address": ambulance.get("address", ""),
                "maps_url": maps_url,
            })

        return {
            "success": True,
            "ambulances": formatted_ambulances,
            "total_found": len(formatted_ambulances),
            "message": (
                f"Found {len(formatted_ambulances)} ambulance services "
                f"nearby (⚠️ EMERGENCY)"
            ),
        }

    except Exception as e:
        logger.error(f"[HospitalSearchTool] Ambulance search error: {e}")
        return {
            "success": False,
            "ambulances": [],
            "total_found": 0,
            "message": f"Error searching ambulances: {str(e)}",
        }


# ══════════════════════════════════════════════════════
# CLINIC SEARCH
# ══════════════════════════════════════════════════════

async def search_nearby_clinics(
    latitude: float,
    longitude: float,
    radius_meters: int = 5000,
    limit: int = 10,
) -> dict:
    """Find nearby private clinics."""
    try:
        logger.info(
            f"[HospitalSearchTool] Finding clinics "
            f"near ({latitude}, {longitude})"
        )

        maps_service = _get_maps_service()
        clinics = await maps_service.search_clinics(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_meters,
            limit=limit,
        )

        formatted_clinics = []
        for clinic in clinics:
            maps_url = clinic.get("maps_url")
            if not maps_url:
                maps_url = _get_maps_service().build_google_maps_url(
                    clinic.get("name", ""),
                    clinic.get("latitude", 0),
                    clinic.get("longitude", 0),
                )
            formatted_clinics.append({
                "name": clinic.get("name", "Clinic"),
                "distance_km": clinic.get("distance_km", 0),
                "phone": clinic.get("phone", ""),
                "address": clinic.get("address", ""),
                "maps_url": maps_url,
            })

        return {
            "success": True,
            "clinics": formatted_clinics,
            "total_found": len(formatted_clinics),
            "message": f"Found {len(formatted_clinics)} clinics nearby",
        }

    except Exception as e:
        logger.error(f"[HospitalSearchTool] Clinic search error: {e}")
        return {
            "success": False,
            "clinics": [],
            "total_found": 0,
            "message": f"Error searching clinics: {str(e)}",
        }


# ══════════════════════════════════════════════════════
# PHARMACY SEARCH
# ══════════════════════════════════════════════════════

async def search_nearby_pharmacies(
    latitude: float,
    longitude: float,
    radius_meters: int = 5000,
    limit: int = 10,
) -> dict:
    """Find nearby pharmacies."""
    try:
        logger.info(
            f"[HospitalSearchTool] Finding pharmacies "
            f"near ({latitude}, {longitude})"
        )

        maps_service = _get_maps_service()
        pharmacies = await maps_service.search_pharmacies(
            latitude=latitude,
            longitude=longitude,
            radius_m=radius_meters,
            limit=limit,
        )

        formatted_pharmacies = []
        for pharmacy in pharmacies:
            maps_url = pharmacy.get("maps_url")
            if not maps_url:
                maps_url = _get_maps_service().build_google_maps_url(
                    pharmacy.get("name", ""),
                    pharmacy.get("latitude", 0),
                    pharmacy.get("longitude", 0),
                )
            formatted_pharmacies.append({
                "name": pharmacy.get("name", "Pharmacy"),
                "distance_km": pharmacy.get("distance_km", 0),
                "phone": pharmacy.get("phone", ""),
                "address": pharmacy.get("address", ""),
                "maps_url": maps_url,
            })

        return {
            "success": True,
            "pharmacies": formatted_pharmacies,
            "total_found": len(formatted_pharmacies),
            "message": f"Found {len(formatted_pharmacies)} pharmacies nearby",
        }

    except Exception as e:
        logger.error(f"[HospitalSearchTool] Pharmacy search error: {e}")
        return {
            "success": False,
            "pharmacies": [],
            "total_found": 0,
            "message": f"Error searching pharmacies: {str(e)}",
        }


# ══════════════════════════════════════════════════════
# MAIN LOCATION-BASED FACILITY SEARCH
# ══════════════════════════════════════════════════════

async def search_facilities_near_location(
    latitude: float,
    longitude: float,
    facility_types: List[str] = None,
    radius_meters: int = 5000,
) -> dict:
    """
    Search for all types of facilities (hospitals, clinics, pharmacies, ambulances).

    Args:
        latitude: Location latitude
        longitude: Location longitude
        facility_types: List of types ["hospitals", "clinics", "pharmacies", "ambulances"]
        radius_meters: Search radius

    Returns:
        Aggregated results for all facility types requested.
    """
    if facility_types is None:
        facility_types = ["hospitals", "clinics", "pharmacies"]

    try:
        logger.info(
            f"[HospitalSearchTool] Multi-facility search "
            f"at ({latitude}, {longitude}) "
            f"for {facility_types}"
        )

        results = {
            "success": True,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
            },
            "facilities": {},
        }

        # Run searches in parallel
        tasks = []
        if "hospitals" in facility_types:
            tasks.append(
                ("hospitals", search_nearby_hospitals(
                    latitude, longitude, radius_meters
                ))
            )
        if "clinics" in facility_types:
            tasks.append(
                ("clinics", search_nearby_clinics(
                    latitude, longitude, radius_meters
                ))
            )
        if "pharmacies" in facility_types:
            tasks.append(
                ("pharmacies", search_nearby_pharmacies(
                    latitude, longitude, radius_meters
                ))
            )
        if "ambulances" in facility_types:
            tasks.append(
                ("ambulances", search_nearby_ambulances(
                    latitude, longitude, radius_meters
                ))
            )

        # Await all tasks
        if tasks:
            names, coros = zip(*tasks)
            responses = await asyncio.gather(*coros)

            for name, response in zip(names, responses):
                results["facilities"][name] = response

        results["message"] = "Multi-facility search completed"
        return results

    except Exception as e:
        logger.error(f"[HospitalSearchTool] Multi-facility error: {e}")
        return {
            "success": False,
            "facilities": {},
            "message": f"Error in facility search: {str(e)}",
        }
