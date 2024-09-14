from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Player(BaseModel):
    name: str
    rank: str
    role1: str
    role2: str
    cant_play: Optional[str] = None
    rank_value: Optional[int] = None

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[str]
    mode: str  # 'rank', 'balanced', or 'random'

# Define a rank mapping to convert ranks to numerical values
rank_mapping = {
    'Iron 4': 1, 'Iron 3': 2, 'Iron 2': 3, 'Iron 1': 4,
    'Bronze 4': 5, 'Bronze 3': 6, 'Bronze 2': 7, 'Bronze 1': 8,
    'Silver 4': 9, 'Silver 3': 10, 'Silver 2': 11, 'Silver 1': 12,
    'Gold 4': 13, 'Gold 3': 14, 'Gold 2': 15, 'Gold 1': 16,
    'Platinum 4': 17, 'Platinum 3': 18, 'Platinum 2': 19, 'Platinum 1': 20,
    'Emerald 4': 21, 'Emerald 3': 22, 'Emerald 2': 23, 'Emerald 1': 24,
    'Diamond 4': 25, 'Diamond 3': 26, 'Diamond 2': 27, 'Diamond 1': 28,
    'Master': 29, 'Grandmaster': 30, 'Challenger': 31
}

@app.get("/")
def create_greeting():
    greeting = "Connected to StackMaker API Version 1.00"
    return greeting

# Function to ensure all roles are filled in both teams
def fill_missing_roles(team1: Dict[str, Optional[Player]], team2: Dict[str, Optional[Player]], players: List[Player], roles: List[str]):
    unassigned_players = [p for p in players if p not in team1.values() and p not in team2.values()]

    for role in roles:
        # Fill missing roles in Team 1
        if not team1[role]:
            assign_to_role(unassigned_players, team1, role)
        # Fill missing roles in Team 2
        if not team2[role]:
            assign_to_role(unassigned_players, team2, role)

# Helper function to assign the highest-ranked unassigned player to a missing role
def assign_to_role(unassigned_players: List[Player], team: Dict[str, Optional[Player]], role: str):
    for player in unassigned_players:
        if role != player.cant_play:
            team[role] = player
            unassigned_players.remove(player)
            break

# Helper function to re-evaluate and swap roles to optimize for highest-ranked players
def reevaluate_and_swap_roles(team: Dict[str, Optional[Player]], players: List[Player], roles: List[str]):
    for role in roles:
        assigned_player = team.get(role)
        for player in players:
            if player and player.rank_value > (assigned_player.rank_value if assigned_player else 0):
                if (player.role1 == role or player.role2 == role) and player not in team.values():
                    # Swap the higher-ranked player in, and reassign the current player
                    unassigned_player = team[role]
                    team[role] = player
                    players.append(unassigned_player)
                    players.remove(player)
                    break

# Function to assign a player to a team role, with priority based on rank
def assign_player_with_priority(team: Dict[str, Optional[Player]], player: Player, role: str) -> bool:
    if not team[role]:
        team[role] = player
        return True
    # If the role is already taken, replace the lower-ranked player if the current player has a higher rank
    elif team[role].rank_value < player.rank_value:
        unassigned_player = team[role]
        team[role] = player
        return unassigned_player
    return False

@app.post("/create-teams")
def create_teams(request: TeamRequest):
    print("Incoming request:", request.dict())
    
    players = request.players
    roles = request.roles
    mode = request.mode.lower()

    # Convert ranks to numerical values for sorting
    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    # Sort players by rank value from highest to lowest for 'rank' mode
    if mode == 'rank':
        players.sort(key=lambda x: x.rank_value, reverse=True)

    # Initialize empty teams
    team1: Dict[str, Optional[Player]] = {role: None for role in roles}
    team2: Dict[str, Optional[Player]] = {role: None for role in roles}

    # First pass: Try to place the top 5 ranked players in Team 1 with priority
    for player in players[:5]:
        if player and not assign_player_with_priority(team1, player, player.role1):
            assign_player_with_priority(team1, player, player.role2)

    # Re-evaluate roles in Team 1 to ensure highest priority based on rank
    reevaluate_and_swap_roles(team1, players, roles)

    # Second pass: Place remaining players in Team 2 and handle remaining Team 1 slots if needed
    for player in players[5:]:
        if player and not assign_player_with_priority(team2, player, player.role1):
            assign_player_with_priority(team2, player, player.role2)

    # Ensure every role is filled exactly once in both teams
    fill_missing_roles(team1, team2, players, roles)

    # Create a list representation of teams for the response
    def create_team_list(team: Dict[str, Optional[Player]]):
        return [
            {"name": player.name, "rank": player.rank, "assigned_role": role}
            for role, player in team.items() if player
        ]

    team1_list = create_team_list(team1)
    team2_list = create_team_list(team2)

    # Print the final teams
    print("Sorted players:", [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player])
    print("Final Team 1:", team1_list)
    print("Final Team 2:", team2_list)
    
    return {
        "sorted_players": [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player],
        "team1": team1_list,
        "team2": team2_list
    }
