import os
import re
import regex
import csv
import json
import urllib.parse
import boto3

'''
Folder structure:

covenants-deeds-images
    -raw
        -mn-ramsey-county
        -wi-milwaukee-county
    -ocr
        -txt
            -mn-ramsey-county
            -wi-milwaukee-county
        -json
            -mn-ramsey-county
            -wi-milwaukee-county
        -stats
            -mn-ramsey-county
            -wi-milwaukee-county
        -hits
            -mn-ramsey-county
            -wi-milwaukee-county
    -web
        -mn-ramsey-county
        -wi-milwaukee-county
'''

s3 = boto3.client('s3')

def load_terms():
    """Load CSV of complex term objects to be tested.
    
    See test_match() documentation for example term object

    Args:
        None

    Returns:
        list of dictionaries, with each dict being a complex term object.
    """
    terms = []

    try:
        # Runtime / deployed
        f = open('./data/mp-search-terms.csv')
    except FileNotFoundError:
        try:
            # Local testing
            f = open('./term_search/data/mp-search-terms.csv')
        except FileNotFoundError:
            raise

    with f as term_csv:
        reader = csv.DictReader(term_csv)
        for row in reader:
            terms.append(row)
        return terms

def load_json(bucket, key):
    content_object = s3.get_object(Bucket=bucket, Key=key)
    file_content = content_object['Body'].read().decode('utf-8')
    return json.loads(file_content)

def save_match_file(results, bucket, key_parts):
    out_key = f"ocr/hits_fuzzy/{key_parts['workflow']}/{key_parts['remainder']}.json"

    s3.put_object(
        Body=json.dumps(results),
        Bucket=bucket,
        Key=out_key,
        StorageClass='GLACIER_IR',
        ContentType='application/json'
    )
    return out_key

def test_match(term_obj, text):
    """Searches for a regex fuzzy match based on a target term object.

    Using Python's 'regex' library (not built-in re), tests if a given term is in the provided text,
    which in the Deed Machine is generally one line of text from an OCRed document.

    Args:
        term_obj: A dictionary object which includes the basic term, a tolerance value
            to control how fuzzy the search can be, and an optional suffix to require for a match
            (usually a word break or space). In order to avoid escape character weirdness, '$b' will be converted to '\\b' in the final regex

            Example term object:
                {
                    'term': 'death certificate',
                    'tolerance': 2,
                    'suffix': '$b',
                    'bool_exception': True,  # Is this an exception term? Not yet being used
                    'exception_type': 'death_cert'  # What type of exception? Not yet being used
                }

            Will produce this regular expression:
                '\\b(?:death certificate){e<=2'}\\b'

            This will search for the string "death certificate" preceded by a word boundary,
            with a fuzziness tolerance of 2, followed by a word boundary

        text: A string to test for the presence of the term

    Returns:
        True or False
    """
    tolerance = ''
    try:
        tolerance_int = int(term_obj['tolerance'])
        if tolerance_int > 0:
            tolerance = '{e<=' + str(term_obj['tolerance']) + '}'
    except:
        raise

    # pattern = regex.compile(f"{term['prefix']}(?:{term['term']}){tolerance}{term['suffix']}".replace('$s', ' '))
    pattern = regex.compile(f"\\b(?:{term_obj['term']}){tolerance}{term_obj['suffix']}".replace('$b', '\\b'))
    # print(pattern)
    if regex.search(pattern, text):
        return True
    return False

def lambda_handler(event, context):
    """ For each term in covenant_flags, check OCR JSON file received from previous step for existance of term. This uses a fuzzy search based on the Python 'regex' library (not the built-in re library). Some of the terms are actually exceptions rather than covenant hits, and once they reach the Django stage, will be used to mark this page as exempt from consideration as being considered as a racial covenant. Common examples of exceptions include birth certificates and military discharges, which often contain racial information but are not going to contain a racial covenant. """
    
    if 'Records' in event:
        # Get the object from a more standard put event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(
            event['Records'][0]['s3']['object']['key'], encoding='utf-8')
        public_uuid = None
        orig = None
    elif 'detail' in event:
        # Get object from step function with this as first step
        bucket = event['detail']['bucket']['name']
        key = event['detail']['object']['key']
        public_uuid = None  # This could be added from DB or by opening previous JSON records, but would slow down this process
        orig = None
    else:
        # Coming from previous step function
        bucket = event['body']['bucket']
        key = event['body']['json']
        public_uuid = event['body']['uuid']
        orig = event['body']['orig']

    try:
        ocr_result = load_json(bucket, key)
    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure it exists and your bucket is in the same region as this function.'.format(key, bucket))
        raise e

    key_parts = re.search(r'ocr/json/(?P<workflow>[A-z\-]+)/(?P<remainder>.+)\.(?P<extension>[a-z]+)', key).groupdict()

    # Extract individual lines of text for analysis
    lines = [block for block in ocr_result['Blocks'] if block['BlockType'] == 'LINE']

    covenant_flags = load_terms()
    # print(covenant_flags)

    results = {}
    for line_num, line in enumerate(lines):
        text_lower = line['Text'].lower()
        for term in covenant_flags:
            if test_match(term, text_lower):
                if term['term'] not in results:
                    results[term['term']] = [line_num]
                else:
                    results[term['term']].append(line_num)

    bool_hit = False
    match_file = None
    if results != {}:
        results['workflow'] = key_parts['workflow']
        results['lookup'] = key_parts['remainder']
        results['uuid'] = public_uuid
        bool_hit = True
        match_file = save_match_file(results, bucket, key_parts)

    return {
        "statusCode": 200,
        "body": {
            "message": "search term fuzzy success",
            "bool_hit": bool_hit,
            "match_file": match_file,
            "uuid": public_uuid,
            "orig": orig
            # "location": ip.text.replace("\n", "")
        }
    }
