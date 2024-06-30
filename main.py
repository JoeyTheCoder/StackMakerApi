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
        assign_ranked_teams(players, teams, roles, is_valid_role, assigned_players)
    elif mode == 'Balanced':
        players.sort(key=lambda x: x.rank_value, reverse=True)
        balanced_teams(players, teams, roles, is_valid_role, assigned_players)
    elif mode == 'Random':
        random.shuffle(players)
        assign_random_teams(players, teams, roles, is_valid_role, assigned_players)

    # Call the reassign_invalid_roles function to correct any invalid role assignments
    if not reassign_invalid_roles(players, teams, roles, is_valid_role, assigned_players):
        logging.error("Failed to create valid teams. Not all roles could be filled.")
        return {"error": "Failed to create valid teams. Not all roles could be filled."}

    return teams

def assign_ranked_teams(players, teams, roles, is_valid_role, assigned_players):
    logging.info("Assigning ranked teams...")
    # Assign primary roles first
    for player in players:
        for team in teams:
            if team[player.role1] is None and is_valid_role(player, player.role1):
                team[player.role1] = player
                assigned_players.add(player.name)
                break

    # Assign secondary roles next
    for player in players:
        if player.name not in assigned_players:
            for team in teams:
                if team[player.role2] is None and is_valid_role(player, player.role2):
                    team[player.role2] = player
                    assigned_players.add(player.name)
                    break

    # Fill in any remaining roles
    fill_remaining_roles(players, teams, roles, assigned_players, is_valid_role)

def balanced_teams(players, teams, roles, is_valid_role, assigned_players):
    logging.info("Assigning balanced teams...")
    num_teams = len(teams)
    team_ranks = [0] * num_teams
    
    for player in players:
        min_team_index = team_ranks.index(min(team_ranks))
        for role in roles:
            if teams[min_team_index][role] is None and is_valid_role(player, role):
                teams[min_team_index][role] = player
                team_ranks[min_team_index] += player.rank_value
                assigned_players.add(player.name)
                break

    # Fill in any remaining roles
    fill_remaining_roles(players, teams, roles, assigned_players, is_valid_role)

def assign_random_teams(players, teams, roles, is_valid_role, assigned_players):
    logging.info("Assigning random teams...")
    # Assign players randomly
    for player in players:
        for team in teams:
            for role in roles:
                if team[role] is None and is_valid_role(player, role):
                    team[role] = player
                    assigned_players.add(player.name)
                    break
            if player.name in assigned_players:
                break

    # Fill in any remaining roles
    fill_remaining_roles(players, teams, roles, assigned_players, is_valid_role)

def fill_remaining_roles(players, teams, roles, assigned_players, is_valid_role):
    logging.info("Filling remaining roles...")
    for team in teams:
        for role in roles:
            if team[role] is None:
                for player in players:
                    if player.name not in assigned_players and is_valid_role(player, role):
                        team[role] = player
                        assigned_players.add(player.name)
                        break

def reassign_invalid_roles(players, teams, roles, is_valid_role, assigned_players):
    logging.info("Reassigning invalid roles...")
    unassigned_players = []

    for team in teams:
        for role, player in team.items():
            if player and not is_valid_role(player, role):
                logging.info(f"Player {player.name} cannot play {role}. Reassigning...")
                assigned_players.remove(player.name)
                unassigned_players.append(player)
                team[role] = None

    if not unassigned_players:
        return True

    for player in unassigned_players:
        assigned = False
        for team in teams:
            for role in roles:
                if team[role] is None and is_valid_role(player, role):
                    team[role] = player
                    assigned_players.add(player.name)
                    assigned = True
                    break
            if assigned:
                break

    # If players are still unassigned, try swapping roles within the team
    for player in unassigned_players:
        if player.name not in assigned_players:
            for team in teams:
                for role in roles:
                    if team[role] is None:
                        for existing_role, existing_player in team.items():
                            if existing_player and is_valid_role(existing_player, role):
                                team[role] = existing_player
                                team[existing_role] = player
                                assigned_players.add(player.name)
                                break
                        if player.name in assigned_players:
                            break
                if player.name in assigned_players:
                    break

    # Final check to see if all roles are filled
    all_roles_filled = all(len([player for player in team.values() if player is not None]) == len(roles) for team in teams)

    if not all_roles_filled:
        logging.error(f"Final roles could not be filled for players: {[player.name for player in unassigned_players if player.name not in assigned_players]}")

    return all_roles_filled

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

    if isinstance(teams, dict) and "error" in teams:
        return teams

    team_lists = create_team_list(teams)

    # Additional check to ensure teams are valid
    for team in team_lists:
        if len(team) != len(roles):
            logging.error("Failed to create valid teams. Not all roles could be filled.")
            return {"error": "Failed to create valid teams. Not all roles could be filled."}

    logging.info(f"Returning teams: {team_lists}")

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
    ],
    "roles": ["Top", "Jungle", "Mid", "Adc", "Support"],
    "mode": "Rank"
}

# Uncomment the following lines to test the function
# import asyncio
# response = asyncio.run(create_teams(example_request))
# print(response)
