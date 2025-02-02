import httpx
import pandas as pd
import numpy as np
import itertools
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PropType:
    name: str
    stat_key: str
    threshold: Optional[float] = None
    prob_threshold: float = 0.85
    alt_lines: List[float] = None
    category: str = "standard"

class ComprehensiveSportsAnalyzer:
    SPORTS_PROPS = {
        'football': {
            'passing': [
                PropType('Pass Yards', 'passing_yards', alt_lines=[200.5, 225.5, 250.5, 275.5, 300.5]),
                PropType('Pass TDs', 'passing_tds', alt_lines=[0.5, 1.5, 2.5, 3.5]),
                PropType('Pass Attempts', 'pass_attempts', alt_lines=[25.5, 30.5, 35.5, 40.5]),
                PropType('Pass Completions', 'pass_completions', alt_lines=[15.5, 20.5, 25.5, 30.5]),
                PropType('Interceptions', 'interceptions', alt_lines=[0.5, 1.5]),
                PropType('Longest Completion', 'longest_completion', alt_lines=[20.5, 25.5, 30.5, 35.5]),
                PropType('First TD Pass', 'first_td_pass', category='special')
            ],
            'rushing': [
                PropType('Rush Yards', 'rushing_yards', alt_lines=[50.5, 75.5, 100.5]),
                PropType('Rush TDs', 'rushing_tds', alt_lines=[0.5, 1.5])
            ],
            'receiving': [
                PropType('Rec Yards', 'receiving_yards', alt_lines=[50.5, 75.5, 100.5]),
                PropType('Rec TDs', 'receiving_tds', alt_lines=[0.5, 1.5])
            ]
        },
        'basketball': {
            'scoring': [
                PropType('Points', 'points', alt_lines=[15.5, 20.5, 25.5]),
                PropType('Rebounds', 'rebounds', alt_lines=[5.5, 7.5, 10.5]),
                PropType('Assists', 'assists', alt_lines=[4.5, 6.5, 8.5])
            ]
        }
    }

    def __init__(self):
        self.client = httpx.Client(timeout=30.0)
        self.correlation_matrix = self._initialize_correlation_matrix()
        self.variance_factors = self._initialize_variance_factors()

    def _initialize_correlation_matrix(self) -> Dict:
        return {
            'football': {
                'passing': {
                    ('passing_yards', 'pass_attempts'): 0.8,
                    ('passing_yards', 'pass_completions'): 0.85,
                    ('pass_attempts', 'pass_completions'): 0.9
                }
            }
        }

    def _initialize_variance_factors(self) -> Dict:
        return {
            'standard': 1.0,
            'alt_lines': 1.2,
            'special': 1.5,
            'parlays': {
                2: 1.1,
                3: 1.2,
                4: 1.3,
                5: 1.4
            }
        }

    def analyze_props(self, player_data: Dict, sport: str, 
                      min_correlation: float = -0.2) -> List[Dict]:
        valid_props = []
        
        for category, props in self.SPORTS_PROPS[sport].items():
            for prop in props:
                for line in (prop.alt_lines or [prop.threshold]):
                    if line is None:
                        continue
                        
                    analysis = self._analyze_single_prop(
                        player_data, prop, line, sport, category
                    )
                    
                    if analysis and analysis['probability'] >= prop.prob_threshold:
                        valid_props.append(analysis)
        
        return self._filter_correlated_props(valid_props, min_correlation)

    def generate_optimal_parlays(self, valid_props: List[Dict], 
                                  min_picks: int = 2, max_picks: int = 5,
                                  min_probability: float = 0.85) -> List[Dict]:
        parlays = []
        
        for n in range(min_picks, max_picks + 1):
            for combo in itertools.combinations(valid_props, n):
                parlay = self._analyze_parlay(combo)
                if parlay['probability'] >= min_probability:
                    parlays.append(parlay)
        
        return sorted(parlays, key=lambda x: x['ev'], reverse=True)

    def _analyze_single_prop(self, player_data: Dict, prop: PropType, 
                             line: float, sport: str, category: str) -> Dict:
        historical = self._get_historical_data(player_data, prop.stat_key)
        if not historical:
            return None

        mean = np.mean(historical)
        std = np.std(historical)
        trend = self._calculate_trend(historical)
        
        matchup_factor = self._calculate_matchup_factor(player_data)
        variance_factor = self.variance_factors[prop.category]
        
        adjusted_mean = mean * matchup_factor * (1 + trend)
        adjusted_std = std * variance_factor

        probability = self._calculate_probability(adjusted_mean, adjusted_std, line)
        ev = self._calculate_ev(probability, line)

        return {
            'prop_name': prop.name,
            'line': line,
            'probability': probability,
            'ev': ev,
            'trend': trend,
            'category': category,
            'stat_key': prop.stat_key
        }

    def _analyze_parlay(self, props: Tuple[Dict]) -> Dict:
        total_correlation = self._calculate_total_correlation(props)
        individual_probs = [p['probability'] for p in props]
        combined_probability = self._calculate_combined_probability(individual_probs, total_correlation)

        ev = self._calculate_combined_ev(props)

        return {
            'combined_probability': combined_probability,
            'ev': ev,
            'props': [p['prop_name'] for p in props]
        }

    def _get_historical_data(self, player_data: Dict, stat_key: str) -> List[float]:
        # Placeholder: Replace with actual historical data fetching logic
        return np.random.normal(loc=50, scale=10, size=20).tolist()

    def _calculate_trend(self, historical: List[float]) -> float:
        return np.polyfit(range(len(historical)), historical, 1)[0]  # Simple linear trend

    def _calculate_matchup_factor(self, player_data: Dict) -> float:
        return 1.0  # Placeholder, adjust based on matchup analysis

    def _calculate_probability(self, adjusted_mean: float, adjusted_std: float, line: float) -> float:
        z_score = (line - adjusted_mean) / adjusted_std
        probability = 1 - (0.5 * (1 + np.erf(z_score / np.sqrt(2))))
        return probability

    def _calculate_ev(self, probability: float, line: float) -> float:
        odds = line / 100  # Assuming American odds
        return (probability * odds) - (1 - probability)

    def _calculate_total_correlation(self, props: Tuple[Dict]) -> float:
        return sum(self.correlation_matrix['football']['passing'].get((p['stat_key'], p2['stat_key']), 0) 
                   for p in props for p2 in props if p != p2)

    def _calculate_combined_probability(self, individual_probs: List[float], total_correlation: float) -> float:
        combined = 1.0
        for prob in individual_probs:
            combined *= prob
        return combined * (1 + total_correlation)  # Adjust for correlation

    def _calculate_combined_ev(self, props: Tuple[Dict]) -> float:
        return sum(p['ev'] for p in props)

# API Functions
def fetch_teams(sport: str, league: str, season: str) -> List[Dict]:
    base_url = f'https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/seasons/{season}/teams'
    response = httpx.get(base_url)
    
    if response.status_code == 200:
        teams_data = response.json()
        # Check the structure of the data returned
        print(teams_data)  # Debugging line to see the response structure
        return teams_data.get('teams', [])  # Adjust based on the actual structure
    else:
        print(f"Error fetching teams for {sport} - {league}: {response.status_code}")
        return []


def fetch_team_roster(team_url: str) -> Dict:
    response = httpx.get(team_url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching team roster: {response.status_code}")
        return {}

def fetch_players(athletes_url: str) -> Dict:
    response = httpx.get(athletes_url)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching players: {response.status_code}")
        return {}

if __name__ == "__main__":
    analyzer = ComprehensiveSportsAnalyzer()
    
    # Example usage:
    teams = fetch_teams("football", "nfl", "2024")
    for team in teams:
        roster = fetch_team_roster(team['url'])
        players = fetch_players(roster.get('athletes', []))
        player_data = analyzer.analyze_props(players, "football")
        parlays = analyzer.generate_optimal_parlays(player_data)

        # Output parlays
        for parlay in parlays:
            print(parlay)
