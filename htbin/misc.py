
# move contents of this file along appropriate names eventualle
import json
import os
import sqlite3

import re
from collections import defaultdict

import pymorphy2

page_data_dir = os.path.dirname(__file__) + '/../out/random_page_data'
# this is single-time-use functionality, so that's okay
wiki_dump_db_path = '/home/klesun/big/deleteMe/wikipedia_dump/ruwiki.db'
recipe_book_path = '/home/klesun/big/p/shmidusic.lv/unversioned/misc/kniga_o_vkusnoj_i_zdorovoj_pische.txt'


def store_random_page_data(params: dict):
    file_name = params['file_name']
    page_data = params['page_data']
    path = page_data_dir + '/' + file_name + '.json'

    if os.path.dirname(path) != page_data_dir:
        raise ValueError('file_name can not contain slashes: '
             + '<br/>' + os.path.dirname(path)
             + '<br/>' + page_data_dir)

    with open(path, 'a') as outfile:
        json.dump(page_data, outfile, indent=2, ensure_ascii=False)
        outfile.write(',\n')

    return 'stored OK'


def get_assorted_food_articles(params: dict) -> list:
    db = sqlite3.connect(wiki_dump_db_path)
    db.row_factory = lambda c,row: {col[0]: row[i] for i,col in enumerate(c.description)}
    db_cursor = db.cursor()

    def exec(article_type):
        sql = '\n'.join([
            'SELECT p.*, ao.food_relevance_score',
            'FROM page p',
            'JOIN article_opinion ao ON p.wiki_id = ao.wiki_id',
            'WHERE 1',
            '  AND ' + ('p.aticle_type IS NULL' if article_type is None else '  p.aticle_type = ?'),
            '  AND ao.definition_noun = "масло"',
            '  AND ao.food_relevance_score IN (4,5)',
            # '  AND ao.rowid IS NULL',
            # '  AND p.food_weight > 10',
            # 'ORDER BY p.food_weight DESC LIMIT 3000',
        ])

        return db_cursor.execute(sql, () if article_type is None else (article_type,))
        # return [row for row in db_cursor.execute(sql, ()) if row['food_relevance_score'] in [4,5]]

    return sorted([]
        # damn OR performance in SQL queries
        + list(exec('taxon'))
        + list(exec(None))
    , key=lambda r: r['food_weight'], reverse=True)


def set_food_article_opinion(params: dict) -> list:
    db = sqlite3.connect(wiki_dump_db_path, timeout=20)
    db_cursor = db.cursor()
    sql = '\n'.join([
        'INSERT OR REPLACE INTO article_opinion',
        '(' + ','.join(params.keys()) + ') VALUES',
        '(' + ','.join([':' + k for k in params.keys()]) + ')',
    ])
    db_cursor.execute(sql, params)
    db.commit()

    return 'stored OK'


def get_food_article_opinions(params: dict) -> list:
    db = sqlite3.connect(wiki_dump_db_path)
    db.row_factory = lambda c, row: {col[0]: row[i] for i, col in enumerate(c.description)}
    db_cursor = db.cursor()
    sql = '\n'.join([
        'SELECT ao.*, p.wiki_title as title',
        'FROM article_opinion ao',
        'JOIN page p ON p.wiki_id = ao.wiki_id',
        'WHERE food_relevance_score > 1',
        '  AND food_relevance_score != 3',
    ])
    return list(db_cursor.execute(sql))


def get_wiki_article_redirects(params: dict) -> list:
    db = sqlite3.connect(wiki_dump_db_path)
    db_cursor = db.cursor()
    return {
        title: main_title
        for title, main_title
        in db_cursor.execute('\n'.join([
            'SELECT s.title, s.main_title',
            'FROM synonyms s',
            'JOIN page p ON p.wiki_title = s.main_title',
            'JOIN article_opinion ao ON ao.wiki_id = p.wiki_id',
            'WHERE ao.food_relevance_score > 1',
            '  AND ao.food_relevance_score != 3',
        ]))
    }


def get_recipe_book(params: dict) -> list:
    with open(recipe_book_path) as f:
        text = f.read()

    morph = pymorphy2.MorphAnalyzer()
    occurByWord = defaultdict(int)
    for match in re.finditer(r'([А-Яа-я\-]+)', text, flags=re.DOTALL):
        nouns = set()
        for parse in morph.parse(match.group(1)):
            if parse.tag.POS == 'NOUN':
                nouns.add(parse.normal_form)
        for noun in nouns:
            occurByWord[noun] += 1

    return occurByWord
