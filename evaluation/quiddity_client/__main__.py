from .client import QuiddityClient

if __name__ == "__main__":
    client = QuiddityClient(username="user", password="pass")
    client.login()
    user_data = client.get_current_user()
    print(user_data)
    docs = client.perform_search(
        dataset_id=8,
        user_input="John Smith",
        collection_id=15,
        class_name="_default",
    )
    print(docs)
