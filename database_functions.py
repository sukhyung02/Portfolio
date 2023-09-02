"""
Fonctions de gestion de la base de données des noms d'équipe/joueur/compétition
"""
import json
import sqlite3
import urllib
import urllib.request
import urllib.error
import datetime
import re
import unidecode

from bs4 import BeautifulSoup
import colorama
import termcolor

import sportsbetting as sb


def get_id_from_competition_name(competition, sport):
    """
    Retourne l'id et le nom tel qu'affiché sur comparateur-de-cotes.fr. Par
    exemple, "Ligue 1" devient "France - Ligue 1"
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT id FROM competitions WHERE competition = "{}" AND sport='{}'
    """.format(competition, sport))
    return c.fetchone()[0]


def get_competition_by_id(_id, site):
    """
    Retourne l'url d'une competition donnée sur un site donné
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT url_{} FROM competitions WHERE id='{}'
    """.format(str(site), _id))
    return c.fetchone()[0]


def get_formatted_name(name, site, sport):
    """
    Uniformisation d'un nom d'équipe/joueur d'un site donné conformément aux noms disponibles sur
    comparateur-de-cotes.fr. Par exemple, "OM" devient "Marseille"
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    res = list(c.execute("""
    SELECT name FROM names WHERE sport="{}" AND name_{}="{}"
    """.format(sport, site, name)))
    c.close()
    try:
        return res[0][0]
    except IndexError:
        if sb.DB_MANAGEMENT:
            colorama.init()
            print(termcolor.colored('{}\t{}{}'.format(site, name,
                                                      colorama.Style.RESET_ALL),
                                    'red'))
            colorama.deinit()
        return "unknown team/player ".upper() + name


def get_competition_id(name, sport):
    """
    Retourne l'id d'une compétition
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT id, competition FROM competitions WHERE sport='{}'
    """.format(sport))
    for line in c.fetchall():
        strings_name = name.lower().split()
        possible = True
        for string in strings_name:
            if string not in line[1].lower():
                possible = False
                break
        if possible:
            return line[0]


def get_competition_url(name, sport, site):
    """
    Retourne l'url d'une compétition sur un site donné
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT competition, url_{} FROM competitions WHERE sport='{}'
    """.format(site, sport))
    for line in c.fetchall():
        strings_name = name.lower().split()
        possible = True
        for string in strings_name:
            if string not in line[0].lower():
                possible = False
                break
        if possible:
            return line[1]


def is_url_in_db(url, site):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT competition FROM competitions WHERE url_{}='{}'
    """.format(site, url))
    return bool(c.fetchone())


def import_teams_by_url(url):
    """
    Ajout dans la base de données de toutes les équipes/joueurs d'une même compétition (url) ayant
    un match prévu sur comparateur-de-cotes.fr
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    sport = soup.find("title").string.split()[-1].lower()
    for line in soup.find_all(["a"]):
        if "href" in line.attrs and "-td" in line["href"] and line.text:
            _id = line["href"].split("-td")[-1]
            if not is_id_in_db(_id):
                c.execute("""
                INSERT INTO names (id, name, sport)
                VALUES ({}, "{}", "{}")
                """.format(_id, line.text, sport))
                conn.commit()
    c.close()


def import_teams_by_sport(sport):
    """
    Ajout dans la base de données de toutes les équipes/joueurs d'un même sport ayant un match prévu
    sur comparateur-de-cotes.fr
    """
    url = "http://www.comparateur-de-cotes.fr/comparateur/" + sport
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    for line in soup.find_all(["a"]):
        if "href" in line.attrs and "-ed" in line["href"] and line.text and sport in line["href"]:
            import_teams_by_url(unidecode.unidecode("http://www.comparateur-de-cotes.fr/"
                                                    + line["href"]))


def import_teams_by_competition_id_thesportsdb(_id):
    url = "https://www.thesportsdb.com/api/v1/json/1/lookup_all_teams.php?id=" + str(-_id)
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    dict_competition = json.loads(soup.text)
    if dict_competition["teams"]:
        for team in dict_competition["teams"]:
            add_id_to_db_thesportsdb(-int(team["idTeam"]))


def is_id_in_db(_id):
    """
    Vérifie si l'id est dans la base de données
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT id FROM names WHERE id="{}"
    """.format(_id))
    for line in c.fetchall():
        return line


def is_in_db(name, sport, site, only_null=True):
    """
    Vérifie si le nom uniformisé de l'équipe est dans la base de données
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    if only_null:
        c.execute("""
        SELECT id, name FROM names WHERE sport="{}" AND name="{}" and name_{} IS NULL
        """.format(sport, name, site))
    else:
        c.execute("""
        SELECT id FROM names WHERE sport="{}" AND name="{}"
        """.format(sport, name))
    return list(c.fetchall())


def is_in_db_site(name, sport, site):
    """
    Vérifie si le nom de l'équipe/joueur tel qu'il est affiché sur un site est dans la base de
    données
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT id FROM names WHERE sport="{}" AND name_{}="{}"
    """.format(sport, site, name))
    for line in c.fetchall():
        return line


def get_formatted_name_by_id(_id):
    """
    Retourne le nom d'une équipe en fonction de son id dans la base de donbées
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT name FROM names WHERE id='{}'
    """.format(_id))
    try:
        return c.fetchone()[0]
    except TypeError:
        add_id_to_db(_id)
        c.execute("""
        SELECT name FROM names WHERE id='{}'
        """.format(_id))
        return c.fetchone()[0]


def add_id_to_db(_id):
    """
    Ajoute l'id d'une équipe/joueur inconnu à la base de données
    """
    if is_id_in_db(_id):  # Pour éviter les ajouts intempestifs (précaution)
        return
    url = "http://www.comparateur-de-cotes.fr/comparateur/football/Angers-td" + str(_id)
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    for line in soup.findAll("a", {"class": "otn"}):
        if str(_id) in line["href"]:
            sport = line["href"].split("/")[1]
            name, category = line.text, None
            if " (" in line.text:
                name, category = line.text.split(" (")
                category.strip(")")
            conn = sqlite3.connect(sb.PATH_DB)
            c = conn.cursor()
            c.execute("""
            INSERT INTO names (id, name, sport, category)
            VALUES ({}, "{}", "{}", "{}")
            """.format(_id, name, sport, category))
            conn.commit()
            c.close()
            break
    else:
        if "Aucun évènement n'est programmé pour" in soup.text:
            name = soup.text.split("Aucun évènement n'est programmé pour")[1].split("\n")[0].strip()
            category = None
            if " (" in name:
                name, category = name.split(" (")
                category = category.strip(")")
            sport = soup.find("div", {"class": "head"}).text.split("(")[-1].strip(")").lower()
            conn = sqlite3.connect(sb.PATH_DB)
            c = conn.cursor()
            c.execute("""
            INSERT INTO names (id, name, sport, category)
            VALUES ({}, "{}", "{}", "{}")
            """.format(_id, name, sport, category))
            conn.commit()
            c.close()


def add_id_to_db_thesportsdb(_id):
    if is_id_in_db(_id):  # Pour éviter les ajouts intempestifs (précaution)
        return
    url = "https://www.thesportsdb.com/api/v1/json/1/lookupteam.php?id=" + str(-_id)
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    dict_team = json.loads(soup.text)
    name = dict_team["teams"][0]["strTeam"]
    sport = (dict_team["teams"][0]["strSport"].lower().replace("soccer", "football")
             .replace("ice_hockey", "hockey-sur-glace"))
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO names (id, name, sport)
    VALUES ({}, "{}", "{}")
    """.format(_id, name, sport))
    conn.commit()
    c.close()


def get_sport_by_id(_id):
    """
    Retourne le sport associé à un id d'équipe/joueur dans la base de données
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT sport FROM names WHERE id='{}'
    """.format(_id))
    try:
        return c.fetchone()[0]
    except TypeError:
        if int(_id) > 0:
            add_id_to_db(_id)
        else:
            add_id_to_db_thesportsdb(_id)
        c.execute("""
        SELECT sport FROM names WHERE id='{}'
        """.format(_id))
        return c.fetchone()[0]


def add_name_to_db(_id, name, site, check=False, date_next_match=None, date_next_match_db=None):
    """
    Ajoute le nom de l'équipe/joueur tel qu'il est affiché sur un site dans la base de données
    """
    sport = get_sport_by_id(_id)
    if is_in_db_site(name, sport, site): #Pour éviter les ajouts intempestifs
        return True
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    name_is_potential_double = sport == "tennis" and any(x in name for x in ["-", "/", "&"])
    formatted_name = get_formatted_name_by_id(_id)
    id_is_potential_double = "&" in formatted_name
    ans = None
    if (name and is_id_available_for_site(_id, site)
            and (not name_is_potential_double ^ id_is_potential_double)):
        if check:
            if sb.INTERFACE:
                sb.QUEUE_TO_GUI.put("Créer une nouvelle donnée pour {} ({}) sur {}\n"
                                    "Nouvelle donnée : {}\n"
                                    "Date du prochain match de l'équipe à ajouter : {}\n"
                                    "Date du prochain match de l'équipe existant dans la db : {}\n"
                                    "Prochaine compétition jouée dans la db : {}\n"
                                    "Catégorie : {}\n"
                                    .format(formatted_name, _id, site, name, date_next_match,
                                            date_next_match_db, get_next_competition(_id), get_category(_id)))
                ans = sb.QUEUE_FROM_GUI.get(True)
            elif not sb.TEST:
                ans = input("Créer une nouvelle entrée pour {} sur {} "
                            "(nouvelle entrée : {}) (y/n)"
                            .format(formatted_name, site, name))
        if not check or ans in ['y', 'Yes']:
            c.execute("""
            UPDATE names
            SET name_{0} = "{1}"
            WHERE _rowid_ = (
                SELECT _rowid_
                FROM names
                WHERE id = {2} AND name_{0} IS NULL
                ORDER BY _rowid_
                LIMIT 1
            );
            """.format(site, name, _id))
        else:
            return False
    else:
        c.execute("""
        SELECT sport, name, name_{} FROM names
        WHERE id = {}
        """.format(site, _id))
        sport, formatted_name, name_site = c.fetchone()
        if name and name != name_site:
            if check:
                if sb.INTERFACE:
                    sb.QUEUE_TO_GUI.put("Créer une nouvelle donnée pour {} sur {}\n"
                                        "Nouvelle donnée : {}\n"
                                        "Donnée déjà existante : {}\n"
                                        "Date du prochain match de l'équipe à ajouter : {}\n"
                                        "Date du prochain match de l'équipe existant dans la db : {}\n"
                                        "Prochaine compétition jouée dans la db : {}\n"
                                        "Catégorie : {}\n"
                                        .format(formatted_name, site, name, name_site, date_next_match,
                                                date_next_match_db, get_next_competition(_id), get_category(_id)))
                    ans = sb.QUEUE_FROM_GUI.get(True)
                elif not sb.TEST:
                    ans = input("Créer une nouvelle entrée pour {} sur {} "
                                "(entrée déjà existante : {}, nouvelle entrée : {}) (y/n)"
                                .format(formatted_name, site, name_site, name))
            if not check or ans in ['y', 'Yes']:
                if name_site and not is_id_available_for_site(_id, site):
                    c.execute("""
                    INSERT INTO names (id, name, sport, category, name_{})
                    VALUES ({}, "{}", "{}", "{}", "{}")
                    """.format(site, _id, formatted_name, sport, get_category(_id), name))
                else:
                    c.execute("""
                    UPDATE names
                    SET name_{0} = "{1}"
                    WHERE _rowid_ = (
                        SELECT _rowid_
                        FROM names
                        WHERE id = {2} AND name_{0} IS NULL
                        ORDER BY _rowid_
                        LIMIT 1
                    );
                    """.format(site, name, _id))
            else:
                return False
    c.close()
    conn.commit()
    return True


def is_id_available_for_site(_id, site):
    """
    Vérifie s'il est possible d'ajouter un nom associé à un site et à un id sans créer de nouvelle
    entrée
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT name_{} FROM names WHERE id = {}
    """.format(site, _id))
    for line in c.fetchall():
        if line[0] is None:
            return True
    return False


def get_close_name(name, sport, site, only_null=True):
    """
    Cherche un nom similaire dans la base de données
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    if only_null:
        c.execute("""
        SELECT id, name FROM names WHERE sport='{}' AND name_{} IS NULL
        """.format(sport, site))
    else:
        c.execute("""
        SELECT id, name FROM names WHERE sport='{}'
        """.format(sport))
    results = []
    for line in c.fetchall():
        if (unidecode.unidecode(name.lower()) in unidecode.unidecode(line[1].lower())
                or unidecode.unidecode(line[1].lower()) in unidecode.unidecode(name.lower())):
            results.append(line)
    return results


def get_close_name2(name, sport, site, only_null=True):
    """
    Cherche un nom similaire dans la base de données en ignorant tous les sigles. Par exemple,
    "Paris SG" devient "Paris"
    """
    name = name.split("(")[0].strip()
    split_name = re.split(r'[ .\-,]', name)
    split_name2 = " ".join([string for string in split_name if (len(string) > 2
                                                                or string != string.upper())])
    if not split_name2:
        return []
    set_name = set(map(lambda x: unidecode.unidecode(x.lower()), split_name))
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    if only_null:
        c.execute("""
        SELECT id, name FROM names WHERE sport='{}' AND name_{} IS NULL
        """.format(sport, site))
    else:
        c.execute("""
        SELECT id, name FROM names WHERE sport='{}'
        """.format(sport))
    results = []
    for line in c.fetchall():
        string_line = line[1].split("(")[0].strip()
        split_line = re.split(r'[ .\-,]', string_line)
        split_line2 = " ".join([string for string in split_line if (len(string) > 2
                                                                    or string != string.upper())])
        if not split_line2:
            continue
        if (unidecode.unidecode(split_name2.lower()) in unidecode.unidecode(split_line2.lower())
                or unidecode.unidecode(split_line2.lower()) in unidecode.unidecode(split_name2
                                                                                   .lower())):
            results.append(line)
            continue
        set_line = set(map(lambda x: unidecode.unidecode(x.lower()), split_line))
        if set_line.issubset(set_name):
            results.append(line)
    return results


def get_close_name3(name, sport, site, only_null=True):
    """
    Cherche un nom proche dans la base de données si le nom est de la forme "Initiale prénom + Nom"
    Par exemple "R. Nadal" renverra "Rafael Nadal"
    """
    results = []
    if "." in name:
        split_name = name.split("(")[0].split(".")
        if len(split_name) == 2 and len(split_name[0]) == 1:
            init_first_name = split_name[0]
            last_name = split_name[1].strip()
            reg_exp = r'{}[a-z]+\s{}'.format(init_first_name, last_name)
            conn = sqlite3.connect(sb.PATH_DB)
            c = conn.cursor()
            if only_null:
                c.execute("""
                SELECT id, name FROM names WHERE sport='{}' AND name_{} IS NULL
                """.format(sport, site))
            else:
                c.execute("""
                SELECT id, name FROM names WHERE sport='{}'
                """.format(sport))
            for line in c.fetchall():
                if re.match(reg_exp, line[1]):
                    results.append(line)
    return results


def get_close_name4(name, sport, site, only_null=True):
    results = set()
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    for bookmaker in sb.BOOKMAKERS:
        if bookmaker in ["barrierebet", "vbet"]:
            continue
        if only_null:
            c.execute("""
            SELECT id, name FROM names WHERE sport='{}' AND name_{}="{}" AND name_{} IS NULL
            """.format(sport, bookmaker, name, site))
        else:
            c.execute("""
            SELECT id, name FROM names WHERE sport='{}' AND name_{}="{}"
            """.format(sport, bookmaker, name))
        for line in c.fetchall():
            results.add(line)
    return list(results)


def get_id_by_site(name, sport, site):
    """
    Retourne l'id d'une équipe/joueur sur un site donné
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT id FROM names WHERE name_{}="{}" AND sport='{}'
    """.format(site, name, sport))
    _id = c.fetchone()
    if _id:
        return _id[0]
    return 0


def get_id_by_opponent(id_opponent, name_site_match, matches):
    """
    Trouve l'id d'une équipe/joueur grâce à l'id de ses futurs adversaires
    """
    url = "http://www.comparateur-de-cotes.fr/comparateur/football/Nice-td" + str(id_opponent)
    date_match = matches[name_site_match]["date"]
    if date_match == "undefined":
        date_match = datetime.datetime.today()
    try:
        soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    except urllib.error.HTTPError:
        return
    get_next_id = False
    for line in soup.find_all(["a", "table"]):
        if get_next_id and "class" in line.attrs and "otn" in line["class"]:
            if line["href"].split("-td")[1] != str(id_opponent):
                return int(line["href"].split("-td")[1])
        if "class" in line.attrs and "bettable" in line["class"]:
            for string in list(line.stripped_strings):
                if " à " in string:
                    date_time = datetime.datetime.strptime(string.lower(), "%A %d %B %Y à %Hh%M")
                    try:
                        if abs(date_time - date_match) <= datetime.timedelta(hours=1):
                            get_next_id = True
                    except TypeError:  # live
                        pass
    return


def get_id_by_opponent_thesportsdb(id_opponent, name_site_match, matches):
    url = "https://www.thesportsdb.com/api/v1/json/1/eventsnext.php?id=" + str(-id_opponent)
    date_match = matches[name_site_match]["date"]
    if date_match == "undefined":
        date_match = datetime.datetime.today()
    try:
        soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    except urllib.error.HTTPError:
        return
    dict_events = json.loads(soup.text)
    if dict_events["events"]:
        for event in dict_events["events"]:
            date_time = (datetime.datetime(*(map(int, event["dateEvent"].split("-"))),
                                           *(map(int, event["strTime"].split(":")[:2])))
                         + datetime.timedelta(hours=2))
            if abs(date_time - date_match) < datetime.timedelta(days=0.5):
                id_home = -int(event["idHomeTeam"])
                id_away = -int(event["idAwayTeam"])
                if id_home == id_opponent:
                    return id_away
                if id_away == id_opponent:
                    return id_home
    return


def get_time_next_match_thesportsdb(id_competition, id_team):
    url = "https://www.thesportsdb.com/api/v1/json/1/eventsnext.php?id=" + str(-id_team)
    try:
        soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
        dict_competition = json.loads(soup.text)
        if dict_competition["events"]:
            for event in dict_competition["events"]:
                if id_competition >= 9999 or str(-id_competition) == event["idLeague"]:
                    date_time = event["dateEvent"]+event["strTime"]
                    return datetime.datetime.strptime(date_time, "%Y-%m-%d%H:%M:%S")+datetime.timedelta(hours=1)
        return 0
    except urllib.error.HTTPError:
        return 0


def get_time_next_match(id_competition, id_team):
    if id_team < 0:
        return get_time_next_match_thesportsdb(id_competition, id_team)
    if id_competition >= 9999:
        url = "http://www.comparateur-de-cotes.fr/comparateur/football/a-td" + str(id_team)
    else:
        url = "http://www.comparateur-de-cotes.fr/comparateur/football/a-ed" + str(id_competition)
    try:
        soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
        for line in soup.find_all("a"):
            if "href" in line.attrs:
                if line["href"].split("td"+str(id_team))[0][-1] == "-":
                    strings = list(line.find_parent("tr").stripped_strings)
                    for string in strings:
                        if " à " in string:
                            return datetime.datetime.strptime(string.lower(), "%A %d %B %Y à %Hh%M")
        return 0
    except urllib.error.HTTPError:
        return 0

def get_next_competition(id_team):
    if id_team > 0:
        url = "http://www.comparateur-de-cotes.fr/comparateur/football/a-td" + str(id_team)
        try:
            soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
            for line in soup.find_all("h1"):
                return line.text.strip()
            return
        except urllib.error.HTTPError:
            return
    return

def get_category(id_team):
    """
    Retourne la catégorie d'une équipe
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT category FROM names WHERE id={}
    """.format(id_team))
    category = c.fetchone()
    if category:
        return category[0]
    return ""
    

def is_matching_next_match(id_competition, id_team, name_team, matches):
    try:
        date_next_match = sorted([matches[x] for x in matches.keys() if name_team in x.split(" - ")],
                                 key=lambda x: x["date"])[0]["date"]
        sport = get_sport_by_id(id_team)
        time_margin = 1
        if id_team < 0:
            return date_next_match == get_time_next_match_thesportsdb(id_competition, id_team)
        return abs(date_next_match-get_time_next_match(id_competition, id_team)) <= datetime.timedelta(hours=time_margin)
    except (IndexError, TypeError): #TypeError si date undefined
        return False


def are_same_double(team1, team2):
    """
    Vérifie si deux équipes de double au tennis sont potentiellement identiques
    """
    return ((team1[0] in team2[0] and team1[1] in team2[1])
            or (team1[0] in team2[1] and team1[1] in team2[0])
            or (team2[0] in team1[0] and team2[1] in team1[1])
            or (team2[0] in team1[1] and team2[1] in team1[0]))


def get_double_team_tennis(team, sport, site, only_null=False):
    """
    Trouve l'équipe de double la plus proche d'une équipe donnée
    """
    assert sport == "tennis"
    if site in ["netbet", "france_pari", "betway"]:
        separator_team = "-"
    elif site in ["betclic", "winamax", "pmu", "zebet", "pinnacle"]:
        separator_team = " / "
        if " / " not in team: # pour zebet (varie entre / et -)
            separator_team = "-"
    elif site in ["bwin", "joa", "parionssport", "pasinobet", "unibet"]:
        separator_team = "/"
    else:  # if site in ["pokerstars"]:
        separator_team = " & "
    results = []
    if separator_team in team:
        complete_names = unidecode.unidecode(team).lower().strip().split(separator_team)
        if site in ["pokerstars", "pasinobet", "pmu"]:
            players = list(map(lambda x: x.split(" ")[-1], complete_names))
        elif site in ["netbet", "france_pari", "winamax", "betway"]:
            players = list(map(lambda x: x.split(".")[-1], complete_names))
        elif site in ["parionssport"]:
            players = complete_names
        elif site in ["bwin"]:
            players = list(map(lambda x: x.split(". ")[-1], complete_names))
        elif site in ["unibet"]:
            if ", " in team:
                players = list(map(lambda x: x.split(", ")[0], complete_names))
            else:
                players = list(map(lambda x: x.split(" ")[0], complete_names))
        elif site in ["betclic"]:
            players = list(map(lambda x: x.split(" ")[0], complete_names))
        elif site in ["zebet", "joa"]:
            if "." in team:
                players = list(map(lambda x: x.split(".")[-1].split("(")[0].strip(), complete_names))
            else:
                players = list(map(lambda x: x.split(" ")[0].strip(), complete_names))
        elif site in ["pinnacle"]:
            players = list(map(lambda x: x.split(" ")[0] if len(x.split(" ")[0]) > 1 else x.split(" ")[1], complete_names))
        players = list(map(lambda x: x.strip(), players))
        conn = sqlite3.connect(sb.PATH_DB)
        c = conn.cursor()
        if only_null:
            c.execute("""
            SELECT id, name FROM names WHERE sport='tennis' AND name LIKE '% & %' AND name_{} IS NULL
            """.format(site))
        else:
            c.execute("""
            SELECT id, name FROM names WHERE sport='tennis' AND name LIKE '% & %'
            """)
        for line in c.fetchall():
            compared_players = unidecode.unidecode(line[1]).lower().split(" & ")
            if are_same_double(players, compared_players):
                results.append(line)
    return results


def get_all_competitions(sport):
    """
    Retourne toutes les compétitions d'un sport donné
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT competition FROM competitions WHERE sport='{0}' AND competition<>'Tout le {0}'
    """.format(sport))
    return ["Tout le "+sport]+sorted(list(map(lambda x: x[0], c.fetchall())))


def get_all_sports():
    """
    Retourne tous les sports disponibles dans la db
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT sport FROM competitions
    """)
    return sorted(list(set(map(lambda x: x[0], c.fetchall()))))


def get_competition_name_by_id(_id):
    """
    Retourne l'url d'une competition donnée sur un site donné
    """
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT competition FROM competitions WHERE id='{}'
    """.format(_id))
    try:
        return c.fetchone()[0]
    except TypeError:
        return


def get_all_current_competitions(sport):
    url = "http://www.comparateur-de-cotes.fr/comparateur/"+sport
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    leagues = []
    for line in soup.find_all("a"):
        if "href" in line.attrs and sport in line["href"] and "ed" in line["href"]:
            id_league = int(line["href"].split("-ed")[-1])
            league_name = line.text.strip()
            league = get_competition_name_by_id(id_league)
            if not league:
                if sb.INTERFACE:
                    sb.QUEUE_TO_GUI.put("Créer une nouvelle compétition : {}"
                                        .format(league_name))
                    ans = sb.QUEUE_FROM_GUI.get(True)
                    if ans == "Yes":
                        conn = sqlite3.connect(sb.PATH_DB)
                        c = conn.cursor()
                        c.execute("""
                        INSERT INTO competitions (id, sport, competition)
                        VALUES ({}, "{}", "{}")
                        """.format(id_league, sport, league_name))
                        conn.commit()
                        c.close()
                        leagues.append(league_name)
            else:
                leagues.append(league)
    return leagues


def is_played_soon(url):
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    for line in soup.find_all("table", attrs={"class":"bettable"}):
        date_time = datetime.datetime.strptime(list(line.stripped_strings)[3].lower(), "%A %d %B %Y à %Hh%M")
        return date_time < datetime.datetime.today()+datetime.timedelta(days=7)

def get_main_competitions(sport):
    url = "http://www.comparateur-de-cotes.fr/comparateur/"+sport
    soup = BeautifulSoup(urllib.request.urlopen(url), features="lxml")
    leagues = []
    for line in soup.find_all(attrs={"class": "subhead"}):
        if any(x in str(line) for x in ["Événements internationaux", "Coupes européennes", "Principaux championnats", "Coupes nationales"]):
            for link in line.findParent().find_all(["a"]):
                if sport in link["href"]:
                    id_league = int(link["href"].split("-ed")[-1])
                    url = "http://www.comparateur-de-cotes.fr/comparateur/{}/a-ed{}".format(sport, str(id_league))
                    if not is_played_soon(url):
                        continue
                    league_name = link.text.strip()
                    league = get_competition_name_by_id(id_league)
                    if not league:
                        if sb.INTERFACE:
                            sb.QUEUE_TO_GUI.put("Créer une nouvelle compétition : {}"
                                                .format(league_name))
                            ans = sb.QUEUE_FROM_GUI.get(True)
                            if ans == "Yes":
                                conn = sqlite3.connect(sb.PATH_DB)
                                c = conn.cursor()
                                c.execute("""
                                INSERT INTO competitions (id, sport, competition)
                                VALUES ({}, "{}", "{}")
                                """.format(id_league, sport, league_name))
                                conn.commit()
                                c.close()
                                leagues.append(league_name)
                    else:
                        leagues.append(league)
            if "Coupes nationales" in str(line) and leagues:
                break
    return leagues


def get_all_names_from_id(_id):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT * FROM names WHERE id="{}"
    """.format(_id))
    results = c.fetchall()
    sport, name = results[0][1:3]
    names_site = set(item for sublist in results for item in sublist[3:] if item)
    for name_site in names_site:
        yield sport, name, name_site


def add_id_to_new_db(_id):
    conn = sqlite3.connect(sb.PATH_DB)
    for sport, name, name_site in get_all_names_from_id(_id):
        c = conn.cursor()
        c.execute("""
        INSERT INTO names_v2 (id, sport, name, name_site)
        VALUES ({}, "{}", "{}", "{}")
        """.format(_id, sport, name, name_site))
    conn.commit()

def get_all_ids():
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT id FROM names
    """)
    for id_ in sorted(list(set(map(lambda x: x[0], c.fetchall())))):
        yield id_

def create_new_db():
    for _id in get_all_ids():
        if _id>133300:
            add_id_to_new_db(_id)

def is_id_consistent(_id):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    select * from names where id={} order by _rowid_
    """.format(_id))
    results = c.fetchall()
    n = len(results)
    list_sites = sb.DB_BOOKMAKERS
    out = True
    for i in range(n):
        if "None" in results[i]:
            print("None", _id)
            out = False
        if not(any(results[i][4:])):
            print("Ligne vide", _id)
            out = False
    for j in range(4, len(results[0])):
        null = False
        previous = None
        for i in range(n):
            if results[i][j] and results[i][j] == previous:
                print("Valeurs identiques", _id, previous, list_sites[j-4])
                out = False
            elif not null and not results[i][j]:
                null = True
            elif i>0 and not previous and results[i][j]:
                print("Valeurs alternées", _id, list_sites[j-4])
                out = False
            previous = results[i][j]
    return out


def is_player_in_db(player):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT name FROM players WHERE name="{}"
    """.format(player))
    if c.fetchall():
        return True
    return False

def is_player_added_in_db(player, site):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    SELECT name FROM players WHERE name_{}="{}"
    """.format(site, player))
    ref_player = c.fetchone()
    if ref_player:
        return ref_player[0]
    return None

def add_player_to_db(player, site):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    UPDATE players
    SET name_{0} = "{1}"
    WHERE _rowid_ = (
        SELECT _rowid_
        FROM players
        WHERE name = "{1}"
        ORDER BY _rowid_
        LIMIT 1
    )
    """.format(site, player))
    c.close()
    conn.commit()

def get_close_player_name(name, site):
    """
    Cherche un nom proche dans la base de données si le nom est de la forme "Initiale prénom + Nom"
    Par exemple "R. Nadal" renverra "Rafael Nadal"
    """
    results = []
    if "." in name:
        split_name = name.split("(")[0].split(".")
    elif "  " in name:
        split_name = name.split("(")[0].split("  ")
    else:
        return results
    if len(split_name) == 2 and len(split_name[0]) == 1:
        init_first_name = split_name[0]
        last_name = split_name[1].strip()
        reg_exp = r'{}[a-zA-Z\-\']+\s{}'.format(init_first_name, last_name)
        conn = sqlite3.connect(sb.PATH_DB)
        c = conn.cursor()
        c.execute("""
        SELECT name FROM players WHERE name_{} IS NULL
        """.format(site))
        for line in c.fetchall():
            if re.match(reg_exp, line[0]):
                results.append(line[0])
    return results

def add_close_player_to_db(player, site):
    close_players = get_close_player_name(player, site)
    if len(set(close_players)) != 1:
        return False
    player_ref = close_players[0]
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    UPDATE players
    SET name_{} = "{}"
    WHERE _rowid_ = (
        SELECT _rowid_
        FROM players
        WHERE name = "{}"
        ORDER BY _rowid_
        LIMIT 1
    )
    """.format(site, player, player_ref))
    c.close()
    conn.commit()
    return player_ref

def add_new_player_to_db(player):
    conn = sqlite3.connect(sb.PATH_DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO players (name)
    VALUES ("{}")
    """.format(player))
    conn.commit()
    c.close()
    
