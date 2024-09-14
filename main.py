from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware
import random

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
    greeting = "Connected to StackMaker API Version 1.01"
    return greeting

def fill_missing_roles(team1, team2, players, roles):
    unassigned_players = [p for p in players if p not in team1.values() and p not in team2.values()]
    for role in roles:
        if not team1[role]:
            assign_to_role(unassigned_players, team1, role)
        if not team2[role]:
            assign_to_role(unassigned_players, team2, role)

def assign_to_role(unassigned_players, team, role):
    for player in unassigned_players:
        if role != player.cant_play:
            team[role] = player
            unassigned_players.remove(player)
            break

def reevaluate_and_swap_roles(team, players, roles):
    for role in roles:
        assigned_player = team.get(role)
        for player in players:
            if player and player.rank_value > (assigned_player.rank_value if assigned_player else 0):
                if (player.role1 == role or player.role2 == role) and player not in team.values():
                    unassigned_player = team[role]
                    team[role] = player
                    players.append(unassigned_player)
                    players.remove(player)
                    break

def assign_player_with_priority(team, player, role):
    if not team[role]:
        team[role] = player
        return True
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

    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    team1: Dict[str, Optional[Player]] = {role: None for role in roles}
    team2: Dict[str, Optional[Player]] = {role: None for role in roles}

    if mode == 'rank':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        for player in players[:5]:
            if player and not assign_player_with_priority(team1, player, player.role1):
                assign_player_with_priority(team1, player, player.role2)
        reevaluate_and_swap_roles(team1, players, roles)
        for player in players[5:]:
            if player and not assign_player_with_priority(team2, player, player.role1):
                assign_player_with_priority(team2, player, player.role2)
        fill_missing_roles(team1, team2, players, roles)

    elif mode == 'random':
        random.shuffle(players)
        for player in players[:5]:
            if player and not assign_player_with_priority(team1, player, player.role1):
                assign_player_with_priority(team1, player, player.role2)
        for player in players[5:]:
            if player and not assign_player_with_priority(team2, player, player.role1):
                assign_player_with_priority(team2, player, player.role2)
        fill_missing_roles(team1, team2, players, roles)

    elif mode == 'balanced':
        # Sort players by rank and split them in a way to balance the teams
        players.sort(key=lambda x: x.rank_value, reverse=True)
        team1_players, team2_players = balance_teams(players)
        for player in team1_players:
            if not assign_player_with_priority(team1, player, player.role1):
                assign_player_with_priority(team1, player, player.role2)
        for player in team2_players:
            if not assign_player_with_priority(team2, player, player.role1):
                assign_player_with_priority(team2, player, player.role2)
        fill_missing_roles(team1, team2, players, roles)

    team1_list = create_team_list(team1)
    team2_list = create_team_list(team2)

    print("Sorted players:", [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player])
    print("Final Team 1:", team1_list)
    print("Final Team 2:", team2_list)
    
    return {
        "sorted_players": [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player],
        "team1": team1_list,
        "team2": team2_list
    }

def create_team_list(team):
    return [
        {"name": player.name, "rank": player.rank, "assigned_role": role}
        for role, player in team.items() if player
    ]

def balance_teams(players):
    team1 = []
    team2 = []
    sum_team1 = 0
    sum_team2 = 0

    for player in players:
        if sum_team1 <= sum_team2:
            team1.append(player)
            sum_team1 += player.rank_value
        else:
            team2.append(player)
            sum_team2 += player.rank_value

    return team1, team2
