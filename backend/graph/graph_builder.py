"""
Transit Network Graph Builder

Builds a time-dependent directed graph from GTFS data where:
- Nodes: Transit stops (with lat/lon attributes)
- Edges: Scheduled connections between stops with time attributes
"""
import pickle
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import networkx as nx
import pandas as pd

from backend.config import settings


class TransitGraphBuilder:
    """Builds time-dependent transit network graphs from GTFS data"""

    def __init__(self, gtfs_dir: str = None):
        """
        Initialize graph builder

        Args:
            gtfs_dir: Path to GTFS directory (defaults to settings.GTFS_EXTRACT_DIR)
        """
        self.gtfs_dir = Path(gtfs_dir or settings.GTFS_EXTRACT_DIR)
        self.graphs = {}  # Dictionary of graphs by day type

        # Load GTFS data
        self.stops_df = None
        self.stop_times_df = None
        self.trips_df = None
        self.routes_df = None
        self.calendar_df = None
        self.calendar_dates_df = None
        self.transfers_df = None

    def load_gtfs_data(self):
        """Load GTFS data files into pandas DataFrames"""
        print("Loading GTFS data files...")

        # Required files
        self.stops_df = pd.read_csv(self.gtfs_dir / 'stops.txt')
        self.stop_times_df = pd.read_csv(self.gtfs_dir / 'stop_times.txt')
        self.trips_df = pd.read_csv(self.gtfs_dir / 'trips.txt')
        self.routes_df = pd.read_csv(self.gtfs_dir / 'routes.txt')
        self.calendar_df = pd.read_csv(self.gtfs_dir / 'calendar.txt')

        # Optional files
        try:
            self.calendar_dates_df = pd.read_csv(self.gtfs_dir / 'calendar_dates.txt')
        except FileNotFoundError:
            self.calendar_dates_df = None
            print("  Note: calendar_dates.txt not found (optional)")

        try:
            self.transfers_df = pd.read_csv(self.gtfs_dir / 'transfers.txt')
        except FileNotFoundError:
            self.transfers_df = None
            print("  Note: transfers.txt not found (optional)")

        print(f"Loaded {len(self.stops_df)} stops")
        print(f"Loaded {len(self.stop_times_df)} stop times")
        print(f"Loaded {len(self.trips_df)} trips")
        print(f"Loaded {len(self.routes_df)} routes")

    def time_to_seconds(self, time_str: str) -> int:
        """
        Convert HH:MM:SS time string to seconds since midnight

        Args:
            time_str: Time in HH:MM:SS format (may exceed 24 hours)

        Returns:
            Seconds since midnight
        """
        if pd.isna(time_str):
            return 0

        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])

        return hours * 3600 + minutes * 60 + seconds

    def get_service_ids_by_day_type(self) -> Dict[str, List[str]]:
        """
        Categorize service_ids into weekday/saturday/sunday

        Returns:
            Dictionary mapping day_type to list of service_ids
        """
        service_ids = {
            'weekday': [],
            'saturday': [],
            'sunday': []
        }

        for _, row in self.calendar_df.iterrows():
            service_id = row['service_id']

            # Weekday: monday-friday all 1, saturday and sunday 0
            if (row['monday'] == 1 and row['tuesday'] == 1 and
                    row['wednesday'] == 1 and row['thursday'] == 1 and
                    row['friday'] == 1 and row['saturday'] == 0 and
                    row['sunday'] == 0):
                service_ids['weekday'].append(service_id)

            # Saturday: only saturday is 1
            elif (row['saturday'] == 1 and row['sunday'] == 0 and
                  row['monday'] == 0 and row['tuesday'] == 0 and
                  row['wednesday'] == 0 and row['thursday'] == 0 and
                  row['friday'] == 0):
                service_ids['saturday'].append(service_id)

            # Sunday: only sunday is 1
            elif (row['sunday'] == 1 and row['saturday'] == 0 and
                  row['monday'] == 0 and row['tuesday'] == 0 and
                  row['wednesday'] == 0 and row['thursday'] == 0 and
                  row['friday'] == 0):
                service_ids['sunday'].append(service_id)

            # If service runs on multiple day types, add to all applicable
            else:
                if row['monday'] == 1 or row['tuesday'] == 1 or row['wednesday'] == 1 or row['thursday'] == 1 or row['friday'] == 1:
                    service_ids['weekday'].append(service_id)
                if row['saturday'] == 1:
                    service_ids['saturday'].append(service_id)
                if row['sunday'] == 1:
                    service_ids['sunday'].append(service_id)

        print(f"Service IDs by day type:")
        print(f"  Weekday: {len(service_ids['weekday'])} services")
        print(f"  Saturday: {len(service_ids['saturday'])} services")
        print(f"  Sunday: {len(service_ids['sunday'])} services")

        return service_ids

    def build_graph_for_day_type(self, day_type: str, service_ids: List[str]) -> nx.DiGraph:
        """
        Build time-dependent graph for a specific day type

        Args:
            day_type: 'weekday', 'saturday', or 'sunday'
            service_ids: List of service_ids active on this day type

        Returns:
            NetworkX directed graph
        """
        print(f"\nBuilding graph for {day_type}...")

        G = nx.DiGraph()

        # Add all stops as nodes
        for _, stop in self.stops_df.iterrows():
            G.add_node(
                stop['stop_id'],
                stop_name=stop['stop_name'],
                lat=stop['stop_lat'],
                lon=stop['stop_lon']
            )

        print(f"  Added {len(G.nodes)} stop nodes")

        # Filter trips by service_id
        trips_on_day = self.trips_df[self.trips_df['service_id'].isin(service_ids)]
        trip_ids = set(trips_on_day['trip_id'])

        print(f"  Filtered to {len(trip_ids)} trips for this day type")

        # Merge trip and route info
        trips_with_routes = trips_on_day.merge(
            self.routes_df[['route_id', 'route_short_name']],
            on='route_id',
            how='left'
        )
        trip_route_map = dict(zip(trips_with_routes['trip_id'],
                                  trips_with_routes['route_short_name']))

        # Filter stop_times to only trips on this day
        stop_times_on_day = self.stop_times_df[
            self.stop_times_df['trip_id'].isin(trip_ids)
        ].copy()

        # Convert times to seconds
        stop_times_on_day['departure_time_sec'] = stop_times_on_day['departure_time'].apply(
            self.time_to_seconds
        )
        stop_times_on_day['arrival_time_sec'] = stop_times_on_day['arrival_time'].apply(
            self.time_to_seconds
        )

        # Sort by trip and sequence
        stop_times_on_day = stop_times_on_day.sort_values(
            ['trip_id', 'stop_sequence']
        )

        # Build edges between consecutive stops on each trip
        edge_count = 0
        for trip_id, trip_stops in stop_times_on_day.groupby('trip_id'):
            trip_stops = trip_stops.sort_values('stop_sequence')
            route_name = trip_route_map.get(trip_id, 'Unknown')

            # Create edges between consecutive stops
            for i in range(len(trip_stops) - 1):
                from_stop = trip_stops.iloc[i]
                to_stop = trip_stops.iloc[i + 1]

                from_stop_id = from_stop['stop_id']
                to_stop_id = to_stop['stop_id']

                departure_time = from_stop['departure_time_sec']
                arrival_time = to_stop['arrival_time_sec']

                # Handle times that go past midnight
                if arrival_time < departure_time:
                    arrival_time += 24 * 3600

                duration = arrival_time - departure_time

                # Add edge (allow multiple edges for different trips/times)
                G.add_edge(
                    from_stop_id,
                    to_stop_id,
                    departure_time=departure_time,
                    arrival_time=arrival_time,
                    duration=duration,
                    trip_id=trip_id,
                    route_name=route_name
                )

                edge_count += 1

        print(f"  Added {edge_count} transit edges")

        # Add transfer edges if transfers.txt exists
        if self.transfers_df is not None:
            transfer_count = 0
            for _, transfer in self.transfers_df.iterrows():
                from_stop = transfer['from_stop_id']
                to_stop = transfer['to_stop_id']

                # Get transfer time (default to 3 minutes if not specified)
                if 'min_transfer_time' in transfer and not pd.isna(transfer['min_transfer_time']):
                    transfer_time = int(transfer['min_transfer_time'])
                else:
                    transfer_time = settings.DEFAULT_TRANSFER_TIME

                # Add transfer edge (time-independent)
                if from_stop in G.nodes and to_stop in G.nodes:
                    G.add_edge(
                        from_stop,
                        to_stop,
                        transfer=True,
                        duration=transfer_time
                    )
                    transfer_count += 1

            print(f"  Added {transfer_count} transfer edges")

        print(f"  Graph complete: {len(G.nodes)} nodes, {len(G.edges)} edges")

        return G

    def build_all_graphs(self):
        """Build graphs for all day types (weekday, saturday, sunday)"""
        print("\n" + "=" * 60)
        print("Building Transit Network Graphs")
        print("=" * 60)

        # Load data
        self.load_gtfs_data()

        # Get service IDs by day type
        service_ids = self.get_service_ids_by_day_type()

        # Build graph for each day type
        for day_type in ['weekday', 'saturday', 'sunday']:
            self.graphs[day_type] = self.build_graph_for_day_type(
                day_type,
                service_ids[day_type]
            )

        print("\n" + "=" * 60)
        print("All graphs built successfully!")
        print("=" * 60)

    def save_graphs(self, graph_dir: str = None):
        """
        Save graphs to pickle files

        Args:
            graph_dir: Directory to save graphs (defaults to settings.GRAPH_DIR)
        """
        graph_dir = Path(graph_dir or settings.GRAPH_DIR)
        graph_dir.mkdir(parents=True, exist_ok=True)

        print("\nSaving graphs...")

        for day_type, graph in self.graphs.items():
            file_path = graph_dir / f"graph_{day_type}.pkl"

            with open(file_path, 'wb') as f:
                pickle.dump(graph, f)

            print(f"  Saved {day_type} graph to {file_path}")

        print("Graphs saved successfully!")

    def load_graphs(self, graph_dir: str = None) -> Dict[str, nx.DiGraph]:
        """
        Load graphs from pickle files

        Args:
            graph_dir: Directory containing graph files

        Returns:
            Dictionary of graphs by day type
        """
        graph_dir = Path(graph_dir or settings.GRAPH_DIR)

        print("Loading graphs...")

        graphs = {}
        for day_type in ['weekday', 'saturday', 'sunday']:
            file_path = graph_dir / f"graph_{day_type}.pkl"

            if not file_path.exists():
                raise FileNotFoundError(f"Graph file not found: {file_path}")

            with open(file_path, 'rb') as f:
                graphs[day_type] = pickle.load(f)

            print(f"  Loaded {day_type} graph: {len(graphs[day_type].nodes)} nodes, {len(graphs[day_type].edges)} edges")

        self.graphs = graphs
        print("Graphs loaded successfully!")

        return graphs


if __name__ == "__main__":
    # Test the graph builder
    builder = TransitGraphBuilder()
    builder.build_all_graphs()
    builder.save_graphs()
