import yaml

def get_polish_airports() -> [str]:
    with open("sources/airports_azair.yaml", "r") as file:
        airport_data = yaml.safe_load(file)

        return airport_data["polish_airports"]

def get_european_airports() -> [str]:
    with open("sources/airports_azair.yaml", "r") as file:
        airport_data = yaml.safe_load(file)

        return airport_data["european_airports"]
