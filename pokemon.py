import re
import sys

import requests
from tabulate import tabulate


class Pokemon:
    def __init__(self, name, gender, species, item):
        self.name = name
        self.gender = gender
        self.species = species
        self.item = item
        self.kills = 0
        self.deaths = 0

    def __repr__(self):
        return f"<Pokemon: \"{self.name}\" ({self.species}), {self.gender}>"


class Player:
    def __init__(self, name):
        self.name = name
        self.pokemons = []


class Parser:
    def __init__(self, battle_text):
        self.battle_text = battle_text

    def _search_battle(self, regex):
        return re.findall(regex, self.battle_text)
    
    def get_players(self):
        matches = self._search_battle("\|player\|p[1|2]\|.*\|.*\|\n")
        players = []
        for match in matches:
            match_split = match.split('|')
            players.append(Player(match_split[3]))
        return players
    
    def _get_pokemon_name(self, species):
        matches = self._search_battle(f"\|switch\|.*\|{species}.*")
        if matches:
            match_split = matches[0].split('|')
            return match_split[2][5:]
        else:
            return None
    
    @staticmethod
    def _find_pokemon_by_name(pokemons, name):
        try:
            return next(filter(lambda x: x.name == name, (*pokemons[0], *pokemons[1])))
        except StopIteration:
            return(None)
    
    @classmethod
    def _find_pokemons_in_chunk(cls, pokemons, chunk):
        ret = []
        flat_pokemons = [*pokemons[0], *pokemons[1]]
        pokemon_names = map(lambda x: x.name, flat_pokemons)
        matches = re.findall('|'.join(pokemon_names), chunk)
        for match in matches:
            if match not in ret:
                ret.append(cls._find_pokemon_by_name(pokemons, match))
        return ret

    def _get_pokemons_kills(self, pokemons):
        battle_chunks = self.battle_text.split("|\n")
        for chunk in battle_chunks:
            matches = re.findall("\|faint\|.*", chunk)
            for match in matches:
                match_split = match.split('|')
                dead_name = match_split[2][5:]
                dead = self._find_pokemon_by_name(pokemons, dead_name)

                pokemons_in_chunk = self._find_pokemons_in_chunk(pokemons, chunk)
                try:
                    killer = next(filter(lambda x: x.name != dead_name, pokemons_in_chunk))
                except StopIteration:
                    raise ValueError(f'Failed to find killer for "{dead_name}" in chunk:\n{chunk}')
                killer.kills += 1
                dead.deaths += 1

    def get_pokemons(self):
        matches = self._search_battle("\|poke\|p[1|2]\|.*\|.*\n")
        pokemons = [[], []]
        for match in matches:
            match_split = match.split('|')
            player = match_split[2]
            info = match_split[3]
            if ', ' in info:
                info_split = info.split(', ')
                species = info_split[0]
                gender = info_split[1]
            else:
                species = info
                gender = ''
            item = (match_split[4] == "item\n")

            pokemon = Pokemon('', gender, species, item)
            if player == "p1":
                pokemons[0].append(pokemon)
            elif player == "p2":
                pokemons[1].append(pokemon)
            else:
                raise ValueError("This script doesn't support more than two players yet.")
        
        for pokemon in (*pokemons[0], *pokemons[1]):
            pokemon.name = self._get_pokemon_name(pokemon.species)
        self._get_pokemons_kills(pokemons)
        return pokemons


if __name__ == "__main__":
    # with open("battle.txt") as f:
    #     battle_text = f.read()
    
    try:
        url = sys.argv[1]
    except IndexError:
        print(f'usage: {sys.argv[0]} <Pokemon Showdown battle URL>')
        sys.exit(1)
    
    if '.log' not in url:
        url = url + '.log'
    if 'replay.pokemonshowdown.com' not in url:
        raise ValueError('This script only works with replay.pokemonshowdown.com URLs.')
    
    res = requests.get(url)
    if res.status_code != 200:
        raise ConnectionError(f'Failed to retrieve battle. Reponse was {res.status_code}\n {res.text}')
   
    parser = Parser(res.text)
    players = parser.get_players()
    players[0].pokemons, players[1].pokemons = parser.get_pokemons()
    
    print('\n=== RESULTS ===\n')
    for player in players:
        rows = []
        for pokemon in player.pokemons:
            rows.append([f'"{pokemon.name}" ({pokemon.species})', pokemon.kills, pokemon.deaths])
        print(tabulate(rows, headers=['Pokemon', 'Kills', 'Deaths']), '\n')
    print('')