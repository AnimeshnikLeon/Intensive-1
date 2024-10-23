import json
import requests
import hashlib
from datetime import datetime
import pandas as pd
from itertools import product
from concurrent.futures import ThreadPoolExecutor, as_completed

class DomClickApi:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "X-Service": "true",
            "Connection": "Keep-Alive",
            "User-Agent": "Android; 12; Google; google_pixel_5; 8.72.0; 8720006; ; NONAUTH"
        })

        # Инициализация (получение cookies)
        self.get("https://api.domclick.ru/core/no-auth-zone/api/v1/ensure_session")
        self.get("https://ipoteka.domclick.ru/mobile/v1/feature_toggles")

    def get(self, url, **kwargs):
        self.__update_headers(url, **kwargs)
        result = self.session.get(url, **kwargs)
        return result

    def __update_headers(self, url, **kwargs):
        url = self.__get_prepared_url(url, **kwargs)
        sault = "ad65f331b02b90d868cbdd660d82aba0"
        timestamp = str(int(datetime.now().timestamp()))
        encoded = (sault + url + timestamp).encode("UTF-8")
        h = hashlib.md5(encoded).hexdigest()
        self.session.headers.update({
            "Timestamp": timestamp,
            "Hash": "v1:" + h,
        })

    def __get_prepared_url(self, url, **kwargs):
        p = requests.models.PreparedRequest()
        p.prepare(method="GET", url=url, **kwargs)
        return p.url

def fetch_offers(dca, params):
    offers_url = 'https://offers-service.domclick.ru/research/v5/offers/'
    offset = 0
    limit = 30
    offers_list = []

    while True:
        res = dca.get(offers_url, params={**params, 'offset': offset, 'limit': limit})

        try:
            data = res.json()
            if not data['success']:
                print(f"Ошибка API: {data['errors']}")
                break

            offers = data.get("result", {}).get("items", [])
            if not offers:
                break

            offers_list.extend(offers)
            offset += limit

        except json.JSONDecodeError:
            print(f"Ошибка: Не удалось декодировать JSON. Ответ сервера:\n{res.text}")
            break

    print(f"Загружено {len(offers_list)} предложений с параметрами: {params}")
    return offers_list

def generate_param_combinations():
    param_grid = {
        'address': ['1d1463ae-c80f-4d19-9331-a1b68a85b553'],
        'deal_type': ['sale'],
        'category': ['living'],
        'offer_type': [['flat'], ['layout']],
        'rooms': [None, 'st', '1', '2', '3', '4+'],
        'time_on_foot__lte': [None, 5, 10, 15, 20],
        'time_by_car__lte': [None, 5, 10, 15, 20],
    }

    for params in product(*param_grid.values()):
        yield dict(zip(param_grid.keys(), params))


def main():
    dca = DomClickApi()
    df = pd.DataFrame()
    max_offers = 20000

    columns_needed = [
        'id',
        'offer_type',
        'object_info.floor',
        'object_info.rooms',
        'object_info.area',
        'price_info.price',
        'price_info.square_price',
        'address.position.lat',
        'address.position.lon',
        'seller.agent.is_agent',
        'published_dt',
        'updated_dt',
        'trade_in',
        'source',
        'ipoteka_rate',
        'has_advance_payment',
        'is_exclusive',
        'status',
        'assignment_sale',
        'online_show',
        'last_price_history_state',
        'is_placement_paid',
        'discount_status.status',
        'discount_status.value',
        'duplicates_offer_count',
        'chat_available',
        'is_auction',
        'address.id',
        'address.kind',
        'address.guid',
        'address.parent_id',
        'address.locality.id',
        'address.locality.kind',
        'address.locality.subkind',
        'address.locality.parent_id',
        'legal_options.is_owner',
        'legal_options.is_agent_owner_approved',
        'pessimization.pessimized',
        'pessimization.pessimization_type',
        'house.floors',
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_offers, dca, params) for params in generate_param_combinations()]

        for future in as_completed(futures):
            offers = future.result()
            temp_df = pd.json_normalize(offers)

            temp_df = temp_df[[col for col in columns_needed if col in temp_df.columns]]  

            df = pd.concat([df, temp_df])
            df.drop_duplicates(subset=['id'], keep='first', inplace=True)

            if len(df) >= max_offers:  
                break

    df.to_csv('offers.csv', index=False)
    print("Данные успешно сохранены в файл 'offers.csv'")


if __name__ == "__main__":
    main()
