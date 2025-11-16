"""
Reachability Calculation using Time-Dependent Transit Graph

Implements time-dependent Dijkstra's algorithm to find all stops
reachable from an origin within a given time budget.
"""
import heapq
from typing import Dict, List, Optional, Tuple

import networkx as nx

from backend.config import settings


class ReachabilityCalculator:
    """Calculates reachability in time-dependent transit networks"""

    def __init__(self, graphs: Dict[str, nx.DiGraph]):
        """
        Initialize calculator with transit graphs

        Args:
            graphs: Dictionary mapping day_type to NetworkX graph
        """
        self.graphs = graphs

    def time_to_seconds(self, time_str: str) -> int:
        """
        Convert HH:MM time string to seconds since midnight

        Args:
            time_str: Time in HH:MM format

        Returns:
            Seconds since midnight
        """
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        return hours * 3600 + minutes * 60

    def calculate_reachability(
        self,
        origin_stop_id: str,
        departure_time: str,
        max_time_minutes: int,
        day_type: str = 'weekday'
    ) -> List[Dict]:
        """
        Calculate all stops reachable from origin within max_time

        Uses time-dependent Dijkstra's algorithm:
        1. Start at origin at departure_time
        2. Track earliest arrival time at each stop
        3. Only take connections that depart after arrival at current stop
        4. Stop when max time budget exceeded

        Args:
            origin_stop_id: Starting stop ID
            departure_time: Departure time in HH:MM format
            max_time_minutes: Maximum travel time in minutes
            day_type: 'weekday', 'saturday', or 'sunday'

        Returns:
            List of reachable stops with travel time and transfer count
        """
        # Get the appropriate graph
        G = self.graphs.get(day_type)
        if G is None:
            raise ValueError(f"Invalid day_type: {day_type}")

        if origin_stop_id not in G.nodes:
            raise ValueError(f"Stop not found: {origin_stop_id}")

        # Convert departure time to seconds
        departure_time_sec = self.time_to_seconds(departure_time)
        max_time_sec = max_time_minutes * 60

        # Track earliest arrival time and number of transfers at each stop
        # Format: {stop_id: (arrival_time, num_transfers)}
        earliest_arrival = {origin_stop_id: (departure_time_sec, 0)}

        # Priority queue: (arrival_time, stop_id, num_transfers)
        pq = [(departure_time_sec, origin_stop_id, 0)]

        # Track which stops we've fully explored
        explored = set()

        while pq:
            current_time, current_stop, num_transfers = heapq.heappop(pq)

            # Skip if we've already explored this stop
            if current_stop in explored:
                continue

            explored.add(current_stop)

            # Check if we've exceeded max time
            if current_time - departure_time_sec > max_time_sec:
                continue

            # Explore outgoing edges
            for neighbor in G.neighbors(current_stop):
                # Get all edges between current_stop and neighbor
                # (there may be multiple connections at different times)
                edge_data = G.get_edge_data(current_stop, neighbor)

                # Handle MultiGraph (multiple edges) vs DiGraph (single edge)
                if isinstance(edge_data, dict) and 'departure_time' in edge_data:
                    # Single edge
                    edges = [edge_data]
                else:
                    # Multiple edges
                    edges = list(edge_data.values()) if isinstance(edge_data, dict) else [edge_data]

                best_arrival = None
                best_transfers = None

                for edge in edges:
                    # Check if this is a transfer edge (time-independent)
                    if edge.get('transfer', False):
                        # Transfer edge - can take immediately
                        arrival_time = current_time + edge['duration']
                        new_transfers = num_transfers + 1

                        if arrival_time - departure_time_sec <= max_time_sec:
                            if best_arrival is None or arrival_time < best_arrival:
                                best_arrival = arrival_time
                                best_transfers = new_transfers

                    else:
                        # Transit edge - must wait for departure
                        dep_time = edge['departure_time']
                        arr_time = edge['arrival_time']

                        # Handle times that wrap past midnight
                        if dep_time < current_time - 24*3600:
                            dep_time += 24*3600
                            arr_time += 24*3600

                        # Can only take this connection if it departs after we arrive
                        if dep_time >= current_time:
                            # Check if within time budget
                            if arr_time - departure_time_sec <= max_time_sec:
                                # Check if this is a transfer (different trip from previous)
                                # For simplicity, count as transfer if we wait > 2 minutes
                                is_transfer = (dep_time - current_time) > 120
                                new_transfers = num_transfers + (1 if is_transfer else 0)

                                if best_arrival is None or arr_time < best_arrival:
                                    best_arrival = arr_time
                                    best_transfers = new_transfers

                # If we found a valid connection to this neighbor
                if best_arrival is not None:
                    # Only update if this is better than previously known route
                    if neighbor not in earliest_arrival or best_arrival < earliest_arrival[neighbor][0]:
                        earliest_arrival[neighbor] = (best_arrival, best_transfers)
                        heapq.heappush(pq, (best_arrival, neighbor, best_transfers))

        # Build result list (excluding origin)
        results = []
        for stop_id, (arrival_time, num_transfers) in earliest_arrival.items():
            if stop_id == origin_stop_id:
                continue

            travel_time_sec = arrival_time - departure_time_sec
            travel_time_min = travel_time_sec / 60.0

            # Get stop info
            stop_data = G.nodes[stop_id]

            results.append({
                'stop_id': stop_id,
                'stop_name': stop_data['stop_name'],
                'lat': stop_data['lat'],
                'lon': stop_data['lon'],
                'travel_time_minutes': round(travel_time_min, 1),
                'num_transfers': num_transfers
            })

        # Sort by travel time
        results.sort(key=lambda x: x['travel_time_minutes'])

        return results

    def calculate_reachability_timeline(
        self,
        origin_stop_id: str,
        departure_time: str,
        max_time_minutes: int,
        time_step_minutes: int,
        day_type: str = 'weekday'
    ) -> List[Dict]:
        """
        Calculate reachability at multiple time intervals for animation

        More efficient than calling calculate_reachability multiple times:
        runs one search and groups results by time intervals.

        Args:
            origin_stop_id: Starting stop ID
            departure_time: Departure time in HH:MM format
            max_time_minutes: Maximum travel time in minutes
            time_step_minutes: Time interval for grouping (e.g., 5 minutes)
            day_type: 'weekday', 'saturday', or 'sunday'

        Returns:
            List of timeline frames, each with elapsed_minutes and reachable_stops
        """
        # Calculate full reachability
        all_reachable = self.calculate_reachability(
            origin_stop_id,
            departure_time,
            max_time_minutes,
            day_type
        )

        # Group by time intervals
        timeline = []

        for step in range(time_step_minutes, max_time_minutes + 1, time_step_minutes):
            # Filter stops reachable within this time step
            stops_at_step = [
                stop for stop in all_reachable
                if stop['travel_time_minutes'] <= step
            ]

            timeline.append({
                'elapsed_minutes': step,
                'reachable_stops': stops_at_step
            })

        return timeline

    def get_stop_info(self, stop_id: str, day_type: str = 'weekday') -> Optional[Dict]:
        """
        Get information about a specific stop

        Args:
            stop_id: Stop ID
            day_type: Day type for graph selection

        Returns:
            Stop information dictionary or None if not found
        """
        G = self.graphs.get(day_type)
        if G is None or stop_id not in G.nodes:
            return None

        stop_data = G.nodes[stop_id]
        return {
            'stop_id': stop_id,
            'stop_name': stop_data['stop_name'],
            'lat': stop_data['lat'],
            'lon': stop_data['lon']
        }

    def get_all_stops(self, day_type: str = 'weekday') -> List[Dict]:
        """
        Get all stops in the network

        Args:
            day_type: Day type for graph selection

        Returns:
            List of all stops
        """
        G = self.graphs.get(day_type)
        if G is None:
            return []

        stops = []
        for stop_id, stop_data in G.nodes(data=True):
            stops.append({
                'stop_id': stop_id,
                'stop_name': stop_data['stop_name'],
                'lat': stop_data['lat'],
                'lon': stop_data['lon']
            })

        # Sort by name for easier searching
        stops.sort(key=lambda x: x['stop_name'])

        return stops
