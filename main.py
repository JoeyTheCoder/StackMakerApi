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

# Add CORS middleware with updated settings to allow requests from your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://stackmaker.ffgang.ch"],  # Update this to your frontend URL
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
    name: constr(strip_whitespace=True, min_length=1, max_length=50, regex=r"^[a-zA-ZäöüÄÖÜß\s\-]+$")
    rank: constr(strip_whitespace=True, regex=r"^(Iron|Bronze|Silver|Gold|Platinum|Emerald|Diamond) \d|Master|Grandmaster|Challenger$")
    role1: constr(strip_whitespace=True, min_length=1, max_length=20)
    role2: Optional[constr(strip_whitespace=True, min_length=0, max_length=20)] = ""  # Allow role2 to be empty
    cant_play: Optional[constr(strip_whitespace=True, min_length=1, max_length=20)] = None
    rank_value: Optional[int] = None
    autofilled: bool = False  # New field to indicate if the player was autofilled

    @validator('rank')
    def validate_rank(cls, v):
        valid_ranks = set(rank_mapping.keys())
        if v not in valid_ranks:
            raise ValueError(f'Invalid rank: {v}')
        return v

class TeamRequest(BaseModel):
    players: List[Player]
    roles: List[constr(strip_whitespace=True, min_length=1, max_length=20)]
    mode: constr(strip_whitespace=True, regex=r"^(rank|balanced|random)$")

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

    # Set max players per team
    max_players_per_team = 5
    
    # Determine number of teams needed
    num_teams = (len(players) // max_players_per_team) + (1 if len(players) % max_players_per_team > 0 else 0)

    # Create dynamic teams as dictionaries with role keys and None as initial values
    teams = [{role: None for role in roles} for _ in range(num_teams)]

    # Assign rank values to players
    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

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
            if assign_player_with_priority(team, player, role):
                assigned = True
                break
        # If not assigned to priority roles, add to unassigned
        if not assigned:
            unassigned_players.append(player)

    # Fill missing roles for each team
    for team in teams:
        fill_missing_roles(team, unassigned_players, roles)

def distribute_balanced_teams(teams, players):
    # Distribute players between all teams in a balanced way
    team_players = [[] for _ in teams]
    sums = [0] * len(teams)

    for player in players:
        min_team_index = sums.index(min(sums))
        team_players[min_team_index].append(player)
        sums[min_team_index] += player.rank_value

    # Assign players to roles in their respective teams
    for team, players in zip(teams, team_players):
        for player in players:
            assign_player_with_priority(team, player, player.role1) or assign_player_with_priority(team, player, player.role2)

def create_team_list(team):
    return [
        {
            "name": f"{player.name} (Autofilled)" if player.autofilled else player.name,
            "rank": player.rank,
            "assigned_role": role
        }
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

def fill_missing_roles(team, unassigned_players, roles):
    """
    Fill missing roles in the team from unassigned players.
    """
    for role in roles:
        if role not in team or team[role] is None:  # Check if the role exists and is unassigned
            assign_to_role(unassigned_players, team, role)

def assign_to_role(unassigned_players, team, role):
    for player in unassigned_players:
        if role != player.cant_play:
            player.autofilled = True  # Mark the player as autofilled
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
