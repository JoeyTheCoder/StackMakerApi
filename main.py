from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
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
    notPlay: Optional[str] = None
    rank_value: Optional[int] = None

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[str]
    mode: str

rank_mapping = {
    'Iron4': 1, 'Iron3': 2, 'Iron2': 3, 'Iron1': 4,
    'Bronze4': 5, 'Bronze3': 6, 'Bronze2': 7, 'Bronze1': 8,
    'Silver4': 9, 'Silver3': 10, 'Silver2': 11, 'Silver1': 12,
    'Gold4': 13, 'Gold3': 14, 'Gold2': 15, 'Gold1': 16,
    'Platinum4': 17, 'Platinum3': 18, 'Platinum2': 19, 'Platinum1': 20,
    'Emerald4': 21, 'Emerald3': 22, 'Emerald2': 23, 'Emerald1': 24,
    'Diamond4': 25, 'Diamond3': 26, 'Diamond2': 27, 'Diamond1': 28,
    'Master': 29, 'Grandmaster': 30, 'Challenger': 31
}

def assign_roles_rank(players, roles):
    players.sort(key=lambda x: x.rank_value, reverse=True)

    team1 = {role: None for role in roles}
    team2 = {role: None for role in roles}
    assigned_players = set()

    def is_valid_role(player, role):
        return player.notPlay != role

    for player in players:
        if player.name not in assigned_players:
            if not team1[player.role1] and is_valid_role(player, player.role1):
                team1[player.role1] = player
                assigned_players.add(player.name)
            elif not team2[player.role1] and is_valid_role(player, player.role1):
                team2[player.role1] = player
                assigned_players.add(player.name)

    for player in players:
        if player.name not in assigned_players:
            if not team1[player.role2] and is_valid_role(player, player.role2):
                team1[player.role2] = player
                assigned_players.add(player.name)
            elif not team2[player.role2] and is_valid_role(player, player.role2):
                team2[player.role2] = player
                assigned_players.add(player.name)

    for player in players:
        if player.name not in assigned_players:
            for role in roles:
                if not team1[role] and is_valid_role(player, role):
                    team1[role] = player
                    assigned_players.add(player.name)
                    break
                elif not team2[role] and is_valid_role(player, role):
                    team2[role] = player
                    assigned_players.add(player.name)
                    break

    def calculate_average_rank(team):
        total_rank = sum(player.rank_value for player in team.values() if player)
        return total_rank / len(roles)

    team1_avg_rank = calculate_average_rank(team1)
    team2_avg_rank = calculate_average_rank(team2)

    if team1_avg_rank < team2_avg_rank:
        for role in roles:
            if team2[role] and team1[role]:
                if team2[role].rank_value > team1[role].rank_value:
                    team1[role], team2[role] = team2[role], team1[role]
                    break

    return team1, team2

def assign_roles_balanced(players, roles):
    players.sort(key=lambda x: x.rank_value, reverse=True)
    team1 = {role: None for role in roles}
    team2 = {role: None for role in roles}
    assigned_players = set()

    def is_valid_role(player, role):
        return player.notPlay != role

    for player in players:
        if player.name not in assigned_players:
            for role in roles:
                if not team1[role] and is_valid_role(player, role):
                    team1[role] = player
                    assigned_players.add(player.name)
                    break
                elif not team2[role] and is_valid_role(player, role):
                    team2[role] = player
                    assigned_players.add(player.name)
                    break

    return team1, team2

def assign_roles_random(players, roles):
    random.shuffle(players)
    team1 = {role: None for role in roles}
    team2 = {role: None for role in roles}
    assigned_players = set()

    for player in players:
        if player.name not in assigned_players:
            for role in roles:
                if not team1[role]:
                    team1[role] = player
                    assigned_players.add(player.name)
                    break
                elif not team2[role]:
                    team2[role] = player
                    assigned_players.add(player.name)
                    break

    return team1, team2

def create_team_list(team):
    team_list = []
    for role, player in team.items():
        if player:
            team_list.append({
                "name": player.name,
                "rank": player.rank,
                "assigned_role": role
            })
    return team_list

@app.get("/")
def create_greeting():
    greeting = "FFG StackMaker"
    return greeting

@app.post("/create-teams")
def create_teams(request: TeamRequest):
    players = request.players
    roles = request.roles
    mode = request.mode

    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    if mode == 'Rank':
        team1, team2 = assign_roles_rank(players, roles)
    elif mode == 'Balanced':
        team1, team2 = assign_roles_balanced(players, roles)
    elif mode == 'Random':
        team1, team2 = assign_roles_random(players, roles)
    else:
        return {"error": "Invalid mode"}

    if team1 is None or team2 is None:
        return {"error": "No optimal solution found."}

    team1_list = create_team_list(team1)
    team2_list = create_team_list(team2)

    return {"team1": team1_list, "team2": team2_list}

# Example usage
example_request = {
    "players": [
        {"name": "Reni", "rank": "Diamond4", "role1": "Adc", "role2": "Mid", "notPlay": "Top"},
        {"name": "Gjunti", "rank": "Diamond3", "role1": "Top", "role2": "Jungle", "notPlay": "Mid"},
        {"name": "Aaron", "rank": "Diamond4", "role1": "Top", "role2": "Jungle", "notPlay": "Support"},
        {"name": "Sandy", "rank": "Master", "role1": "Mid", "role2": "Adc", "notPlay": "Jungle"},
        {"name": "Merlin", "rank": "Platinum1", "role1": "Mid", "role2": "Jungle", "notPlay": "Support"},
        {"name": "Chruune", "rank": "Diamond4", "role1": "Support", "role2": "Top", "notPlay": "Adc"},
        {"name": "Mäc", "rank": "Bronze4", "role1": "Support", "role2": "Jungle", "notPlay": "Mid"},
        {"name": "Albo", "rank": "Platinum4", "role1": "Adc", "role2": "Mid", "notPlay": "Support"},
        {"name": "Arno", "rank": "Silver3", "role1": "Support", "role2": "Adc", "notPlay": "Top"},
        {"name": "Joey", "rank": "Silver1", "role1": "Support", "role2": "Top", "notPlay": "Jungle"}
    ],
    "roles": ["Top", "Jungle", "Mid", "Adc", "Support"],
    "mode": "Balanced"
}

response = create_teams(TeamRequest(**example_request))
print(response)
