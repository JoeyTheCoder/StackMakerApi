from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, constr, validator
from typing import List, Optional, Dict
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.status import HTTP_429_TOO_MANY_REQUESTS
import random
import bleach

# Initialize the limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stackmaker.ffgang.ch"],  # Adjust based on the allowed frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(HTTP_429_TOO_MANY_REQUESTS, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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

class Player(BaseModel):
    name: constr(strip_whitespace=True, min_length=1, max_length=50, pattern=r"^[\wäöüÄÖÜß\s\-\!\@\#\$\%\^\&\*\(\)\[\]\{\}\:\;\,\.\?\~]+$")
    rank: constr(strip_whitespace=True, pattern=r"^(Iron|Bronze|Silver|Gold|Platinum|Emerald|Diamond) \d|Master|Grandmaster|Challenger$")
    role1: constr(strip_whitespace=True, min_length=1, max_length=20)
    role2: constr(strip_whitespace=True, min_length=1, max_length=20)
    cant_play: Optional[constr(strip_whitespace=True, min_length=1, max_length=20)] = None
    rank_value: Optional[int] = None

    @validator('rank')
    def validate_rank(cls, v):
        valid_ranks = set(rank_mapping.keys())
        if v not in valid_ranks:
            raise ValueError(f'Invalid rank: {v}')
        return v

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[constr(strip_whitespace=True, min_length=1, max_length=20)]
    mode: constr(strip_whitespace=True, pattern=r"^(rank|balanced|random)$")

def sanitize_inputs(player: Player) -> Player:
    player.name = bleach.clean(player.name)
    player.role1 = bleach.clean(player.role1)
    player.role2 = bleach.clean(player.role2)
    if player.cant_play:
        player.cant_play = bleach.clean(player.cant_play)
    return player

@app.get("/")
@limiter.limit("10/minute")
def create_greeting(request: Request):
    greeting = "Connected to StackMaker API Version 1.01"
    return greeting

@app.post("/create-teams")
@limiter.limit("5/minute")
async def create_teams(request: Request, team_request: TeamRequest):
    print("Incoming request:", team_request.dict())
    players = [sanitize_inputs(player) for player in team_request.players]
    roles = team_request.roles
    mode = team_request.mode.lower()

    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    # Determine the number of teams needed
    max_players_per_team = len(roles)  # Each team should have exactly one of each role
    num_teams = (len(players) + max_players_per_team - 1) // max_players_per_team

    # Create empty teams dynamically based on the number of teams required
    teams = [{role: None for role in roles} for _ in range(num_teams)]

    # Distribute players among teams based on the selected mode
    if mode == 'rank':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        assign_players_to_teams(players, teams, roles)

    elif mode == 'random':
        random.shuffle(players)
        assign_players_to_teams(players, teams, roles)

    elif mode == 'balanced':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        balanced_assign(players, teams, roles)

    # Convert teams to a list format for response
    teams_list = [create_team_list(team) for team in teams]

    print("Sorted players:", [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player])
    for i, team in enumerate(teams_list, start=1):
        print(f"Final Team {i}:", team)

    return {
        "teams": teams_list
    }

def assign_players_to_teams(players, teams, roles):
    team_size = len(teams[0])  # Number of roles per team

    # First, assign players based on their preferred roles
    unassigned_players = []

    for i, player in enumerate(players):
        team_index = i % len(teams)  # Round-robin assignment to distribute evenly among teams
        team = teams[team_index]
        assigned = assign_player_with_priority(team, player, player.role1)

        if not assigned:
            assigned = assign_player_with_priority(team, player, player.role2)

        if not assigned:
            unassigned_players.append(player)

    # Fill missing roles in all teams
    for team in teams:
        fill_missing_roles(team, unassigned_players, roles)

def fill_missing_roles(team, unassigned_players, roles):
    for role in roles:
        if role not in team or team[role] is None:  # Check if the role exists and is unassigned
            assigned = assign_to_role(unassigned_players, team, role)
            if not assigned:
                print(f"Unable to assign any player to role: {role}")

def assign_to_role(unassigned_players, team, role):
    for player in unassigned_players:
        if role != player.cant_play and player not in team.values():
            team[role] = player
            unassigned_players.remove(player)
            return True
    return False

def balanced_assign(players, teams, roles):
    # Assign players in a balanced way
    team_players = [[] for _ in teams]
    sums = [0] * len(teams)

    for player in players:
        min_team_index = sums.index(min(sums))
        team_players[min_team_index].append(player)
        sums[min_team_index] += player.rank_value

    # Assign players to roles in their respective teams
    for team, team_player_list in zip(teams, team_players):
        unassigned_players = []
        for player in team_player_list:
            assigned = assign_player_with_priority(team, player, player.role1) or assign_player_with_priority(team, player, player.role2)
            if not assigned:
                unassigned_players.append(player)
        fill_missing_roles(team, unassigned_players, roles)

def assign_player_with_priority(team, player, role):
    if not team[role]:
        team[role] = player
        return True
    elif team[role].rank_value < player.rank_value:
        unassigned_player = team[role]
        team[role] = player
        return unassigned_player
    return False

def create_team_list(team):
    return [
        {"name": player.name, "rank": player.rank, "assigned_role": role}
        for role, player in team.items() if player
    ]
