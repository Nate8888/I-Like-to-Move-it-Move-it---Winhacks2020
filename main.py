# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import string
import random
import json

from flask import Flask, render_template, request, redirect
from google.auth.transport import requests
from google.cloud import datastore
import google.oauth2.id_token

firebase_request_adapter = requests.Request()

# [START gae_python37_datastore_store_and_fetch_user_times]
datastore_client = datastore.Client()

# [END gae_python37_datastore_store_and_fetch_user_times]
app = Flask(__name__)

def randomStringDigits(stringLength=6):
    """Generate a random string of letters and digits """
    lettersAndDigits = string.ascii_letters + string.digits
    return ''.join(random.choice(lettersAndDigits) for i in range(stringLength))
# def store_time(dt):
#     entity = datastore.Entity(key=datastore_client.key('visit'))
#     entity.update({
#         'timestamp': dt
#     })
#
#     datastore_client.put(entity)
# def fetch_times(limit):
#     query = datastore_client.query(kind='visit')
#     query.order = ['-timestamp']
#
#     times = query.fetch(limit=limit)
#
#     return times

#TODO Check if the email is the owner of the entry before deleting lol
def delete_entry(email,keyidfromtheentry):
    key = datastore_client.key('UserEntry',str(keyidfromtheentry))
    datastore_client.delete(key)


def get_entries_by_email(email):
    query = datastore_client.query(kind='UserEntry')
    query.add_filter('createdby', '=', email)
    #query.order = ["starttime"]
    results = list(query.fetch())
    return results #Return list of entry objects from datastore

#TODO, check if the entry is available, check if the user can afford...
def claim_entry(email, keyidfromtheentry):

    key = datastore_client.key('UserEntry',str(keyidfromtheentry))
    task = datastore_client.get(key)
    thecost = int(task['cost'])

    currentuser =  datastore_client.key('User',email)
    theUser = datastore_client.get(currentuser)
    theUser['greenpoints'] = int(theUser['greenpoints'])-thecost
    datastore_client.put(theUser)

    emailoftheowner = task['createdby']
    ownerOfTheEntryObject =  datastore_client.key('User',emailoftheowner)

    actualOwner = datastore_client.get(ownerOfTheEntryObject)

    actualOwner['greenpoints'] = int(actualOwner['greenpoints'])+thecost
    datastore_client.put(actualOwner)

    task['claimed'] = 'true'
    task['claimedby'] = email
    datastore_client.put(task)


def get_all_available_entities():
    # time_in_hours_now = (time.time())/360
    query = datastore_client.query(kind='UserEntry')
    query.add_filter('claimed', '=', "false")
    # query.add_filter('endtime', '>', time_in_hours_now)

    all_entries = list(query.fetch())

    return all_entries


def create_entry(email, type, location, costOfGreenPoints): #Email, type="Bike", "Skateboard", "Scooter", "Umbrella"}, location[] lat,long, time in hrs


    complete_key = datastore_client.key('UserEntry',randomStringDigits(12))
    task = datastore.Entity(key=complete_key)

    task.update({
        'createdby':email,
        'type':type,
        'latitude':location[0],
        'longitude':location[1],
        'cost': costOfGreenPoints,
        'claimed': "false",
        'claimedby':""
    })

    datastore_client.put(task)
    print("Put in the datastore!")

def create_user(email):
    complete_key = datastore_client.key('User', email)

    task = datastore.Entity(key=complete_key)

    task.update({
        'greenpoints':100
    })

    datastore_client.put(task)


def does_user_exist(email):
    thekey = datastore_client.key('User', email) #Make a key with the email

    query = datastore_client.get(thekey)
    # query.order = ['-greenpoints']

    if query == None:
        return False
    return True

def update_points(email, amtofpoints, increase): #Email, update with amtofpoints + 5

    key = datastore_client.key('User',email)
    task = datastore_client.get(key)

    task['greenpoints'] = amtofpoints+increase

    datastore_client.put(task)


def get_amount_of_points(email):
    thekey = datastore_client.key('User', email) #Make a key with the email

    query = datastore_client.get(thekey)
    # query.order = ['-greenpoints']

    points = query['greenpoints']

    return points #Return amount of greenpoints from the user.

# [END gae_python37_datastore_store_and_fetch_user_times]


# [START gae_python37_datastore_render_user_times]
@app.route('/map')
def getMap():
    # Verify Firebase auth.
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    list_of_all_datastore_objects = []

    if id_token:
        try:
            # Verify the token against the Firebase Auth API. This example
            # verifies the token on each page load. For improved performance,
            # some applications may wish to cache results in an encrypted
            # session store (see for instance
            # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)

            if does_user_exist(claims['email']):
                print("User Exists")
            else:
                create_user(claims['email'])
            # update_points(claims['email'],currentAmountOfPoints)
            list_of_all_datastore_objects = get_all_available_entities()

        # 'createdby':email,
        # 'type':type,
        # 'latitude':location[0],
        # 'longitude':location[1],
        # 'cost': costOfGreenPoints,
        # 'claimed': "false",
        # 'claimedby':""

            listWithEverything = []
            for each_entry_object in list_of_all_datastore_objects:
                localDict = {}
                localDict['id'] = each_entry_object.key.name
                localDict['lat'] = each_entry_object['latitude']
                localDict['lon'] = each_entry_object['longitude']
                localDict['type'] = each_entry_object['type']
                localDict['cost'] = each_entry_object['cost']
                listWithEverything.append(localDict)

            return render_template('map.html', all_available_entries=listWithEverything)
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)

    return render_template('index.html',user_data=claims, error_message=error_message)


@app.route('/')
def root():
    # Verify Firebase auth.
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    currentAmountOfPoints = 0

    if id_token:
        try:
            # Verify the token against the Firebase Auth API. This example
            # verifies the token on each page load. For improved performance,
            # some applications may wish to cache results in an encrypted
            # session store (see for instance
            # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)

            if does_user_exist(claims['email']):
                currentAmountOfPoints = get_amount_of_points(claims['email'])
            else:
                create_user(claims['email'])
            # update_points(claims['email'],currentAmountOfPoints)
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)

    return render_template(
        'index.html',
        user_data=claims, error_message=error_message, points=currentAmountOfPoints)
# [END gae_python37_datastore_render_user_times]

@app.route('/createentry',methods=['POST'])
def createEntryPage():
    # Verify Firebase auth.
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    currentAmountOfPoints = 0

    if id_token:
        try:
            # Verify the token against the Firebase Auth API. This example
            # verifies the token on each page load. For improved performance,
            # some applications may wish to cache results in an encrypted
            # session store (see for instance
            # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)

            type = request.form.get('type')
            latitude = request.form.get('lat')
            long = request.form.get('long')
            cost = request.form.get('cost')

            if does_user_exist(claims['email']):
                print("User Exists!")
                #email, type, location, costOfGreenPoints
                create_entry(claims['email'], type,[latitude,long], cost)
            else:
                create_user(claims['email'])
            # update_points(claims['email'],currentAmountOfPoints)
            return redirect("/map")
        except ValueError as exc:
            # This will be raised if the token is expired or any other
            # verification checks fail.
            error_message = str(exc)
    return redirect("/")


# @app.route('/getallentries')
# def AllEntries():
#     # Verify Firebase auth.
#     id_token = request.cookies.get("token")
#     error_message = None
#     claims = None
#     currentAmountOfPoints = 0
#     list_of_all_datastore_objects = []
#     if id_token:
#         try:
#             # Verify the token against the Firebase Auth API. This example
#             # verifies the token on each page load. For improved performance,
#             # some applications may wish to cache results in an encrypted
#             # session store (see for instance
#             # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
#             claims = google.oauth2.id_token.verify_firebase_token(
#                 id_token, firebase_request_adapter)
#
#             if does_user_exist(claims['email']):
#                 print("User Exists!")
#                 #email, type, location, time, costOfGreenPoints
#             else:
#                 create_user(claims['email'])
#                 time.sleep(1.2)
#             list_of_all_datastore_objects = get_all_available_entities()
#             # update_points(claims['email'],currentAmountOfPoints)
#         except ValueError as exc:
#             # This will be raised if the token is expired or any other
#             # verification checks fail.
#             error_message = str(exc)
#
#     return render_template(
#         'results.html', user_data=claims, error_message=error_message, all_entries=list_of_all_datastore_objects)


@app.route('/claimentry', methods=['POST'])
def claimSpecificEntry():
        # Verify Firebase auth.
    id_token = request.cookies.get("token")
    error_message = None
    claims = None
    currentAmountOfPoints = 0
    list_of_all_datastore_objects = []

    if id_token:
        try:
            # Verify the token against the Firebase Auth API. This example
            # verifies the token on each page load. For improved performance,
            # some applications may wish to cache results in an encrypted
            # session store (see for instance
            # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
            claims = google.oauth2.id_token.verify_firebase_token(
                id_token, firebase_request_adapter)

            theid = request.form.get('entryid')
            #theemail = request.form.get('emailfromtheentry')
            if does_user_exist(claims['email']):
                print("User Exists!")
            else:
                create_user(claims['email'])

            claim_entry(claims['email'], theid)
            time.sleep(1.2)
            return redirect("/myclaimedentries")
        except ValueError as exc:
                    # This will be raised if the token is expired or any other
                    # verification checks fail.
            error_message = str(exc)

    return redirect("/")


@app.route('/deleteentry', methods=['POST'])
def delete_specific_entry():
            # Verify Firebase auth.
        id_token = request.cookies.get("token")
        error_message = None
        claims = None
        currentAmountOfPoints = 0
        list_of_all_datastore_objects = []

        if id_token:
            try:
                # Verify the token against the Firebase Auth API. This example
                # verifies the token on each page load. For improved performance,
                # some applications may wish to cache results in an encrypted
                # session store (see for instance
                # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)

                theid = request.form.get('entryid')
                #theemail = request.form.get('emailfromtheentry')
                if does_user_exist(claims['email']):
                    print("User Exists!")
                else:
                    create_user(claims['email'])

                delete_entry(claims['email'],theid)
                time.sleep(1.2)
                return redirect('/myentries')
            except ValueError as exc:
                        # This will be raised if the token is expired or any other
                        # verification checks fail.
                error_message = str(exc)

        return redirect('/')

@app.route('/myentries')
def get_all_entries_createbyme():
            # Verify Firebase auth.
        id_token = request.cookies.get("token")
        error_message = None
        claims = None
        currentAmountOfPoints = 0
        allentriesownedbyme = []

        if id_token:
            try:
                # Verify the token against the Firebase Auth API. This example
                # verifies the token on each page load. For improved performance,
                # some applications may wish to cache results in an encrypted
                # session store (see for instance
                # http://flask.pocoo.org/docs/1.0/quickstart/#sessions).
                claims = google.oauth2.id_token.verify_firebase_token(
                    id_token, firebase_request_adapter)

                theid = request.form.get('entryid')
                #theemail = request.form.get('emailfromtheentry')
                if does_user_exist(claims['email']):
                    print("User Exists!")
                else:
                    create_user(claims['email'])

                allentriesownedbyme = get_entries_by_email(claims['email'])

                time.sleep(1.2)

                return render_template('myentries.html', user_data=claims, error_message=error_message, all_entries=allentriesownedbyme)
            except ValueError as exc:
                        # This will be raised if the token is expired or any other
                        # verification checks fail.
                error_message = str(exc)
        return redirect('/')


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
