# Copyright (c) 2001-2016, Canal TP and/or its affiliates. All rights reserved.
#
# This file is part of Navitia,
#     the software to build cool stuff with public transport.
#
# Hope you'll enjoy and contribute to this project,
#     powered by Canal TP (www.canaltp.fr).
# Help us simplify mobility and open public transport:
#     a non ending quest to the responsive locomotion way of traveling!
#
# LICENCE: This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# Stay tuned using
# twitter @navitia
# IRC #navitia on freenode
# https://groups.google.com/d/forum/navitia
# www.navitia.io

import os
from flask_restful import reqparse, abort
import flask_restful
from pymongo.errors import PyMongoError, DuplicateKeyError
from tartare import app
from tartare.core import models
import logging
from tartare.interfaces import schema
from marshmallow import ValidationError


class Contributor(flask_restful.Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('id', location='json')
        parser.add_argument('name', location='json')
        parser.add_argument('data_prefix', location='json')

        args = parser.parse_args()
        contributor_schema = schema.ContributorSchema(strict=True)

        try:
            contributor = contributor_schema.load(args).data
        except ValidationError as err:
            return {'error': err.messages}, 400

        try:
            contributor.save()
        except DuplicateKeyError as e:
            logging.getLogger(__name__).exception('impossible to add contributor {}, data_prefix already used ({})'.format(contributor, args['data_prefix']))
            return {'error': str(e)}, 400
        except PyMongoError as e:
            logging.getLogger(__name__).exception('impossible to add contributor {}'.format(contributor))
            return {'error': str(e)}, 500

        return {'contributor': contributor_schema.dump(contributor).data}, 201

    def get(self, contributor_id=None):
        if contributor_id:
            c = models.Contributor.get(contributor_id)
            if c is None:
                abort(404)
            result = schema.ContributorSchema().dump(c)
            return {'contributor': result.data}, 200
        contributors = models.Contributor.all()
        return {'contributors': schema.ContributorSchema(many=True).dump(contributors).data}, 200

    def delete(self, contributor_id):
        c = models.Contributor.delete(contributor_id)
        if c == 0:
            abort(404)
        return {'contributor': None}, 204

    def patch(self, contributor_id):
        parser = reqparse.RequestParser()
        parser.add_argument('id', location='json')
        parser.add_argument('name', location='json')
        parser.add_argument('data_prefix', location='json')
        args = parser.parse_args()

        # we remove the null values in the parser to keep only setted values
        # (else mongo will erase the other values)
        args = {k: v for k, v in args.items() if v}

        # "data_prefix" field is not modifiable, impacts of the modification need to be checked. The previous value needs to be checked for an error
        contributor = models.Contributor.get(contributor_id)
        if contributor is None:
            abort(404)

        if ('data_prefix' in args) and (contributor.data_prefix != args['data_prefix']):
            return {'error': 'The modification of the data_prefix is not possible ({} => {})'.format(contributor.data_prefix, args['data_prefix'])}, 400
        if ('id' in args) and (contributor.id != args['id']):
            return {'error': 'The modification of the id is not possible'}, 400

        try:
            contributor = models.Contributor.update(contributor_id, args)
        except PyMongoError as e:
            logging.getLogger(__name__).exception('impossible to update contributor with dataset {}'.format(args))
            return {'error': str(e)}, 500

        return {'contributor': schema.ContributorSchema().dump(contributor).data}, 200