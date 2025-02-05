class Remove204ResponseContentMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process the request (if needed)
        response = self.get_response(request)

        if response.status_code == 204:
            # nodejs crashes when a 204 response has a body
            # but when you use HttpResponse(None, status=204) it still has a body:
            # b'None'
            # so we need to remove the body and content-length header
            # logging.warning("Response is 204")
            # logging.warning(response.content)
            # logging.warning(response["content-length"])
            response.content = ""
            response["content-length"] = 0

        return response
