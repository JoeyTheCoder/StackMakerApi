from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import random
import logging

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

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

def assign_roles(players, roles, mode):
    num_teams = len(players) // 5
    teams = [{role: None for role in roles} for _ in range(num_teams)]
    assigned_players = set()

    def is_valid_role(player, role):
        return player.notPlay != role

    if mode == 'Rank':
        players.sort(key=lambda x: x.rank_value, reverse=True)
    elif mode == 'Balanced':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        balanced_teams(players, teams, roles, is_valid_role, assigned_players)
    elif mode == 'Random':
        random.shuffle(players)

    for player in players:
        for team in teams:
            for role in roles:
                if not team[role] and is_valid_role(player, role):
                    team[role] = player
                    assigned_players.add(player.name)
                    break
            if player.name in assigned_players:
                break

    for player in players:
        if player.name not in assigned_players:
            for team in teams:
                for role in roles:
                    if not team[role] and is_valid_role(player, role):
                        team[role] = player
                        assigned_players.add(player.name)
                        break
                if player.name in assigned_players:
                    break

    return teams

def balanced_teams(players, teams, roles, is_valid_role, assigned_players):
    num_teams = len(teams)
    for i, player in enumerate(players):
        team_index = i % num_teams
        for role in roles:
            if not teams[team_index][role] and is_valid_role(player, role):
                teams[team_index][role] = player
                assigned_players.add(player.name)
                break

def create_team_list(teams):
    team_lists = []
    for team in teams:
        team_list = []
        for role, player in team.items():
            if player:
                team_list.append({
                    "name": player.name,
                    "rank": player.rank,
                    "assigned_role": role
                })
        team_lists.append(team_list)
    return team_lists

@app.get("/")
def create_greeting():
    greeting = "FFG StackMaker"
    return greeting

@app.post("/create-teams")
async def create_teams(request: Request):
    data = await request.json()
    logging.info(f"Received data: {data}")

    try:
        team_request = TeamRequest(**data)
    except Exception as e:
        logging.error(f"Error parsing request: {e}")
        return {"error": str(e)}

    players = team_request.players
    roles = team_request.roles
    mode = team_request.mode

    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    if mode not in ['Rank', 'Balanced', 'Random']:
        return {"error": "Invalid mode"}

    teams = assign_roles(players, roles, mode)

    team_lists = create_team_list(teams)

    return {"teams": team_lists}

# Example usage
example_request = {
    "players": [
        {"name": "Merlin", "rank": "Emerald2", "role1": "Mid", "role2": "Jungle", "notPlay": "Support"},
        {"name": "Reni", "rank": "Emerald3", "role1": "Adc", "role2": "Top", "notPlay": "Jungle"},
        {"name": "Indi", "rank": "Diamond4", "role1": "Jungle", "role2": "Top", "notPlay": ""},
        {"name": "Mäc", "rank": "Bronze4", "role1": "Support", "role2": "Jungle", "notPlay": ""},
        {"name": "Aaron", "rank": "Emerald1", "role1": "Top", "role2": "Jungle", "notPlay": ""},
        {"name": "Joey", "rank": "Gold3", "role1": "Support", "role2": "Mid", "notPlay": "Jungle"},
        {"name": "Arno", "rank": "Silver3", "role1": "Support", "role2": "Adc", "notPlay": "Jungle"},
        {"name": "Sandy", "rank": "Master", "role1": "Mid", "role2": "Jungle", "notPlay": "Top"},
        {"name": "Albo", "rank": "Platinum1", "role1": "Adc", "role2": "Mid", "notPlay": ""},
        {"name": "Chruune", "rank": "Diamond4", "role1": "Support", "role2": "Top", "notPlay": "Adc"},
        {"name": "1", "rank": "Iron1", "role1": "Top", "role2": "Jungle", "notPlay": ""},
        {"name": "2", "rank": "Iron3", "role1": "Jungle", "role2": "Mid", "notPlay": ""},
        {"name": "3", "rank": "Iron4", "role1": "Mid", "role2": "Adc", "notPlay": ""},
        {"name": "4", "rank": "Iron4", "role1": "Adc", "role2": "Support", "notPlay": ""},
        {"name": "5", "rank": "Iron4", "role1": "Support", "role2": "Top", "notPlay": ""}
    ],
    "roles": ["Top", "Jungle", "Mid", "Adc", "Support"],
    "mode": "Balanced"
}

response = create_teams(example_request)
print(response)
