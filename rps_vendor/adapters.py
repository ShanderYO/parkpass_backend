class RpsCreateParkingSessionAdapter(object):

    def __init__(self, request_dict):
        self.request_dict = request_dict

    def adapt(self):
        client_id = self.request_dict.get('client_id', None)
        parking_id = self.request_dict.get('parking_id', None)
        if client_id is None or parking_id is None:
            return None
        self.request_dict["session_id"] = str(parking_id)+"&"+str(client_id)
        return self.request_dict
