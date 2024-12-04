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

# Import Google OR-Tools
from ortools.sat.python import cp_model

# Initialize the limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Include localhost for testing
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
        pattern=r"^[\wäöüÄÖÜß\s\-\!\@\#\$\%\^\&\*\(\)\[\]\{\}\:\;\,\.\?\~]+$"
    )
    rank: constr(strip_whitespace=True) = Field(
        pattern=r"^(Iron|Bronze|Silver|Gold|Platinum|Emerald|Diamond) \d|Master|Grandmaster|Challenger$"
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
        pattern=r"^(rank|balanced|random)$"
    )

def sanitize_inputs(player: Player) -> Player:
    player.name = bleach.clean(player.name)
    player.role1 = bleach.clean(player.role1)
    player.role2 = bleach.clean(player.role2)
    if player.cant_play:
        player.cant_play = bleach.clean(player.cant_play)
    return player

def sanitize_role(role: str) -> str:
    return role.strip().capitalize()

# Rate limit this route to 25 requests per minute per client
@app.get("/")
@limiter.limit("25/minute")
def create_greeting(request: Request):
    greeting = "Connected to StackMaker API Version 1.01"
    return greeting

# Create teams endpoint with dynamic team creation using OR-Tools
@app.post("/create-teams")
@limiter.limit("25/minute")
async def create_teams(request: Request, team_request: TeamRequest):
    print("Incoming request:", team_request.dict())
    players = team_request.players
    roles = [sanitize_role(role) for role in team_request.roles]
    mode = team_request.mode.lower()

    # Assign rank values to players
    for player in players:
        player.rank_value = rank_mapping.get(player.rank, 0)

    # Sanitize inputs
    players = [sanitize_inputs(player) for player in players]

    # Determine number of teams needed
    max_players_per_team = len(roles)  # Assuming one player per role
    num_teams = max(1, (len(players) + max_players_per_team - 1) // max_players_per_team)

    # Adjust number of teams to prefer teams of 5
    if len(players) >= 10:
        num_teams = len(players) // 5
    elif len(players) % 5 == 0:
        num_teams = len(players) // 5
    else:
        # Try to make as many teams of 5 as possible
        num_teams = len(players) // 5 + 1

    # Use OR-Tools to create teams
    teams = create_teams_with_ortools(players, roles, num_teams, mode)

    if not teams:
        raise HTTPException(status_code=400, detail="Unable to create teams with the given constraints.")

    # Define the desired role order
    role_order = ['Top', 'Jungle', 'Mid', 'Adc', 'Support']

    # Convert teams to lists for the response
    teams_list = [create_team_list(team, role_order) for team in teams]

    print("Teams formed:")
    for i, team in enumerate(teams_list, start=1):
        print(f"Team {i}: {team}")

    return {
        "teams": teams_list
    }

def create_teams_with_ortools(players, roles, num_teams, mode):
    # Set a fixed random seed for consistency
    random.seed(42)

    if mode == 'random':
        # Shuffle the players list to create random teams
        random.shuffle(players)

        # Create empty teams
        teams = [{} for _ in range(num_teams)]
        role_index = 0

        # Assign players to teams and roles in a round-robin fashion
        for i, player in enumerate(players):
            team_index = i % num_teams
            role = roles[role_index % len(roles)]
            teams[team_index][role] = player
            role_index += 1

        return teams

    # If not in random mode, continue using OR-Tools as before
    model = cp_model.CpModel()
    num_players = len(players)
    num_roles = len(roles)

    # Variables
    x = {}
    for p, player in enumerate(players):
        for r, role in enumerate(roles):
            for t in range(num_teams):
                x[p, r, t] = model.NewBoolVar(f'x_{p}_{r}_{t}')

    # Constraints
    # Each player is assigned to exactly one role in one team
    for p in range(num_players):
        model.Add(sum(x[p, r, t] for r in range(num_roles) for t in range(num_teams)) == 1)

    # Each role in each team is filled by exactly one player
    for t in range(num_teams):
        for r in range(num_roles):
            model.Add(sum(x[p, r, t] for p in range(num_players)) == 1)

    # Players cannot be assigned to roles they can't play
    for p, player in enumerate(players):
        for t in range(num_teams):
            for r, role in enumerate(roles):
                if role.lower() == (player.cant_play or '').lower():
                    model.Add(x[p, r, t] == 0)

    # Team size constraints: Teams can only have sizes of 1,2,3, or 5
    allowed_sizes = [1, 2, 3, 5]
    for t in range(num_teams):
        team_size = model.NewIntVar(1, num_players * num_roles, f'team_size_{t}')
        model.Add(team_size == sum(x[p, r, t] for p in range(num_players) for r in range(num_roles)))
        # Enforce that team_size is one of the allowed sizes
        model.AddAllowedAssignments([team_size], [(size,) for size in allowed_sizes])

    # Symmetry-breaking constraints: Enforce team ordering by total rank
    team_ranks = []
    for t in range(num_teams):
        team_rank = model.NewIntVar(0, num_players * 31, f'team_rank_{t}')
        model.Add(team_rank == sum(
            x[p, r, t] * players[p].rank_value
            for p in range(num_players) for r in range(num_roles)
        ))
        team_ranks.append(team_rank)
    for t in range(num_teams - 1):
        model.Add(team_ranks[t] >= team_ranks[t + 1])

    # Objective function
    objective_terms = []

    W_main = 1000
    W_secondary = 500
    W_autofill = -1000
    W_rank = 10
    W_team5 = 1000

    # Maximize role preference satisfaction and handle rank priorities
    for p, player in enumerate(players):
        for t in range(num_teams):
            # Main role preference
            if player.role1 in roles:
                r_main = roles.index(player.role1)
                objective_terms.append(x[p, r_main, t] * W_main)
                # Rank priority for main role
                objective_terms.append(x[p, r_main, t] * player.rank_value * W_rank)
            # Secondary role preference
            if player.role2 in roles:
                r_secondary = roles.index(player.role2)
                objective_terms.append(x[p, r_secondary, t] * W_secondary)
            # Penalty for roles outside preferences
            for r, role in enumerate(roles):
                if role not in [player.role1, player.role2]:
                    objective_terms.append(x[p, r, t] * W_autofill)

    # Prefer teams of 5 players
    for t in range(num_teams):
        team_size = model.NewIntVar(1, num_players * num_roles, f'team_size_for_objective_{t}')
        model.Add(team_size == sum(x[p, r, t] for p in range(num_players) for r in range(num_roles)))
        is_team_of_5 = model.NewBoolVar(f'is_team_of_5_{t}')
        model.Add(team_size == 5).OnlyEnforceIf(is_team_of_5)
        model.Add(team_size != 5).OnlyEnforceIf(is_team_of_5.Not())
        objective_terms.append(is_team_of_5 * W_team5)

    # Mode-specific objectives
    if mode == 'balanced':
        # Minimize the difference between the highest and lowest team ranks
        max_team_rank = model.NewIntVar(0, num_players * 31, 'max_team_rank')
        min_team_rank = model.NewIntVar(0, num_players * 31, 'min_team_rank')
        model.AddMaxEquality(max_team_rank, team_ranks)
        model.AddMinEquality(min_team_rank, team_ranks)
        model.Minimize(max_team_rank - min_team_rank)
    elif mode == 'rank':
        # Maximize the total rank in Team 1
        team1_rank = team_ranks[0]
        objective_terms.append(team1_rank)
        # Prioritize higher-ranked players in preferred roles
        # (Already handled in the objective_terms above)

    # Set the objective
    if mode != 'balanced':
        model.Maximize(sum(objective_terms))

    # Solve the model
    solver = cp_model.CpSolver()
    solver.parameters.random_seed = 42  # Set a fixed random seed for the solver
    status = solver.Solve(model)

    # Check the solution
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Extract assignments
        teams = [{} for _ in range(num_teams)]
        for t in range(num_teams):
            for p, player in enumerate(players):
                for r, role in enumerate(roles):
                    if solver.BooleanValue(x[p, r, t]):
                        teams[t][role] = player
        return teams
    else:
        print("No solution found.")
        return None

def create_team_list(team, role_order):
    return [
        {"name": team[role].name, "rank": team[role].rank, "assigned_role": role}
        for role in role_order if role in team and team[role]
    ]

def get_player_team(teams, player):
    for index, team in enumerate(teams, start=1):
        if player in team.values():
            return f"Team {index}"
    return None

def get_player_role(teams, player):
    for team in teams:
        for role, assigned_player in team.items():
            if assigned_player == player:
                return role
    return None
