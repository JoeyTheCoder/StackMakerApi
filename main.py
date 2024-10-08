from fastapi import FastAPI, HTTPException, Depends, Request
from pydantic import BaseModel, Field, constr, validator
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
    allow_origins=["https://stackmaker.ffgang.ch"],  # Ensure this matches exactly with your frontend URL
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
    name: constr(strip_whitespace=True, min_length=1, max_length=50) = Field(
        regex=r"^[\wäöüÄÖÜß\s\-\!\@\#\$\%\^\&\*\(\)\[\]\{\}\:\;\,\.\?\~]+$"
    )
    rank: constr(strip_whitespace=True) = Field(
        regex=r"^(Iron|Bronze|Silver|Gold|Platinum|Emerald|Diamond) \d|Master|Grandmaster|Challenger$"
    )
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
    mode: constr(strip_whitespace=True) = Field(
        regex=r"^(rank|balanced|random)$"
    )

def sanitize_inputs(player: Player) -> Player:
    player.name = bleach.clean(player.name)
    player.role1 = bleach.clean(player.role1)
    player.role2 = bleach.clean(player.role2)
    if player.cant_play:
        player.cant_play = bleach.clean(player.cant_play)
    return player

# Rate limit this route to 10 requests per minute per client
@app.get("/")
@limiter.limit("10/minute")
def create_greeting(request: Request):
    greeting = "Connected to StackMaker API Version 1.01"
    return greeting

# Create teams endpoint with dynamic team creation
@app.post("/create-teams")
@limiter.limit("5/minute")
async def create_teams(request: Request, team_request: TeamRequest):
    print("Incoming request:", team_request.dict())
    players = team_request.players
    roles = team_request.roles
    mode = team_request.mode.lower()

    # Assign rank values to players
    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    # Determine number of teams needed
    max_players_per_team = 5
    num_teams = (len(players) // max_players_per_team) + (1 if len(players) % max_players_per_team > 0 else 0)

    # Create dynamic teams as dictionaries with role keys and None as initial values
    teams = [{role: None for role in roles} for _ in range(num_teams)]

    if mode == 'rank':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        distribute_players_among_teams(teams, players, roles, mode)

    elif mode == 'random':
        random.shuffle(players)
        distribute_players_among_teams(teams, players, roles, mode)

    elif mode == 'balanced':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        distribute_balanced_teams(teams, players)

    # Convert teams to lists for the response
    teams_list = [create_team_list(team) for team in teams]

    print("Sorted players:", [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player])
    for i, team in enumerate(teams_list, start=1):
        print(f"Final Team {i}:", team)
    
    return {
        "sorted_players": [{"name": player.name, "rank": player.rank, "rank_value": player.rank_value} for player in players if player],
        "teams": teams_list
    }

def distribute_players_among_teams(teams, players, roles, mode):
    team_size = len(teams[0])  # Assuming all teams have the same role structure

    unassigned_players = []

    for i, player in enumerate(players):
        team_index = i // team_size
        if team_index >= len(teams):
            unassigned_players.append(player)
            continue

        team = teams[team_index]
        role_priority = [player.role1, player.role2]

        # Attempt to assign the player to the most prioritized role in the team
        assigned = False
        for role in role_priority:
            if role in team and assign_player_with_priority(team, player, role):
                assigned = True
                break
        # If not assigned to priority roles, add to unassigned
        if not assigned:
            unassigned_players.append(player)

    # Fill missing roles for each team
    for team in teams:
        fill_missing_roles(team, unassigned_players, roles)

    # Ensure all players are accounted for by re-checking unassigned players
    if unassigned_players:
        print("Warning: Unassigned players remaining:", [p.name for p in unassigned_players])

def distribute_balanced_teams(teams, players):
    # Distribute players between all teams in a balanced way
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

    # Ensure no players are left unaccounted
    remaining_unassigned = [p for team_players_list in team_players for p in team_players_list if p not in team.values()]
    if remaining_unassigned:
        print("Remaining unassigned players after balanced distribution:", [p.name for p in remaining_unassigned])

def create_team_list(team):
    return [
        {"name": player.name, "rank": player.rank, "assigned_role": role}
        for role, player in team.items() if player
    ]

def fill_missing_roles(team, unassigned_players, roles):
    for role in roles:
        if role not in team or team[role] is None:
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

def assign_player_with_priority(team, player, role):
    if not team[role]:
        team[role] = player
        return True
    elif team[role].rank_value < player.rank_value:
        unassigned_player = team[role]
        team[role] = player
        return unassigned_player
    return False
