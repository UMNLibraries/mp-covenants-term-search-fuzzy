import io
import json
import toml
import boto3
import pytest

from term_search import app

with open('samconfig.toml', 'r') as f:
    config = toml.load(f)
    s3_bucket = config['default']['deploy']['parameters']['s3_bucket']
    s3_region = config['default']['deploy']['parameters']['region']


s3 = boto3.client('s3')


def get_s3_match_json(bucket, key):
    response = s3.get_object(Bucket=bucket, Key=key)
    return json.loads(response['Body'].read())


def build_lambda_input(bucket, infile_json):

    return {
        "statusCode": 200,
        "body": {
            "message": "hello world",
            "bucket": bucket,
            # "orig": "raw/mn-sherburne-county/batch3/R3Part2/Abstract 88291.jpg",
            "json": infile_json,
            # "txt": "ocr/txt/mn-sherburne-county/batch3/R3Part2/Abstract 88291.txt",
            # "stats": "ocr/stats/mn-sherburne-county/batch3/R3Part2/Abstract 88291__69727524d8d04bfc99ee0f0bf22584e0.json",
            "uuid": "69727524d8d04bfc99ee0f0bf22584e0",
            # "handwriting_pct": 0.01
        }
    }

@pytest.fixture()
def death_cert_table_input_1():
    """ Generates API GW Event"""
    return build_lambda_input(s3_bucket, "ocr/json/mn-sherburne-county/RECEXPORT/Abstract 103872_SPLITPAGE_2.json")


def term_test_builder(term, term_variations, true_or_false=True):
    covenant_flags = app.load_terms()
    term_fuzzy = [f for f in covenant_flags if f['term'] == term][0]

    for test_term in term_variations:
        assert app.test_match(term_fuzzy, test_term) == true_or_false

def test_term_basic():
    """Manually testing select terms loaded via spreadsheet"""

    term_test_builder('caucasian', [' caucasian', ' caucasian ', 'cau-casian', 'caucasion', 'cau-casion', 'cauca-sion', 'caucausian', 'caucasin', 'aucasian', 'caboasian', 'can-casia', 'cancasian', 'capcasian', 'caticasian', 'cau casian', 'cauc- asia', 'caucã¡sian', 'caucagian', 'caucaison', 'caucasia', 'caucasiã¡n', 'caucasiã¤n', 'caucasiar', 'caucasiari', 'caucasien', 'caucasioan', 'caucasisian', 'caucasism', 'caucassian', 'caucastan', 'caucastian', 'cauccasian', 'cauccian', 'caucesian', 'caudasian', 'caueasian', 'caugasian', 'cauoasian', 'causas ian', 'causcasian', 'caussian', 'concasion', 'coucasion', 'daucasi', 'daucasian', 'daucasion', 'gaucasian', 'gaucasion', 'saucasian', 'vaucasian', 'gaucasian cage', 'caueasien rage', 'casian', '-casian'], True)

    term_test_builder('caucasian', ['concession', 'gaucas', 'cã¡ugasiah rage'], False)

    term_test_builder('aryan', [' aryan'], True)
    term_test_builder('aryan', ['Maryanne'], False)

    term_test_builder('negro', ['negro', 'negroes', 'negroid', 'given to negroes'], True)

    term_test_builder('colored', ['colored', 'c olored', 'cblored'], True)

    # term_test_builder('alien', ['alien'], True)
    # term_test_builder('alien', ['valient', 'dalience', 'daliance', 'alienate'], False)

    term_test_builder('indian', ['indian', ' indian '], True)
    term_test_builder('indian', ['indiana'], False)

    term_test_builder('semitic', ['semetic', 'semitic', 'simitic'], True)

    term_test_builder('not white', ['people who are not white.'], True)


def test_term_csv_read():
    covenant_flags = app.load_terms()
    caucasian_row = [f for f in covenant_flags if f['term'] == 'caucasian'][0]
    caucasian_variations = [t.replace("'", "") for t in caucasian_row['test_variations'].split(',')]

    print(caucasian_variations)

    assert len(caucasian_variations) > 10

def test_terms_from_csv():
    """Manually testing ALL terms loaded via spreadsheet against their listed positive and negative variations."""
    covenant_flags = app.load_terms()

    for term_obj in covenant_flags:
        test_variations = [t.replace("'", "") for t in term_obj['test_variations'].split(',')]
        negative_variations = [t.replace("'", "") for t in term_obj['negative_variations'].split(',')]

        # Testing all the strings that should match in the CSV
        for variation in test_variations:
            assert app.test_match(term_obj, variation) == True

        # Testing all the strings that should NOT match in the CSV
        for variation in negative_variations:
            assert app.test_match(term_obj, variation) == False
    

def test_death_cert_table_input_1(death_cert_table_input_1):

    ret = app.lambda_handler(death_cert_table_input_1, "")
    data = ret["body"]
    print(data)

    assert ret["statusCode"] == 200
    assert "message" in ret["body"]
    assert data["message"] == "hello world"
    
    assert data["bool_hit"] == True
    assert data["match_file"] != None

    hit_json = get_s3_match_json(s3_bucket, data["match_file"])

    assert len(hit_json['date of death']) > 0
    assert len(hit_json['name of deceased']) > 0
