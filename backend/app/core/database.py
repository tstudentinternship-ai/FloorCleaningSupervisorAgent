from azure.cosmos import CosmosClient,PartitionKey
from app.core.config import COSMOS_URL,COSMOS_KEY,DATABASE_NAME

client=CosmosClient(COSMOS_URL,COSMOS_KEY)
db = client.create_database_if_not_exists(id="FLOOR-CLEANER")
# db=client.get_database_client(DATABASE_NAME)

# checkpoints_container=db.get_container_client("checkpoints")
# scan_container=db.get_container_client("scan_events")

checkpoints_container=db.create_container_if_not_exists(
    id="checkpoints",
    partition_key=PartitionKey(path="/store_id")
)

users_container=db.create_container_if_not_exists(
    id="USERS",
    partition_key=PartitionKey(path="/user_id")
)

stores_container = db.create_container_if_not_exists(
    id="stores",
    partition_key=PartitionKey(path="/id")
)

tags_container = db.create_container_if_not_exists(
    id="tags",
    partition_key=PartitionKey(path="/store_id")
)

settings_container = db.create_container_if_not_exists(
    id="settings",
    partition_key=PartitionKey(path="/id")
)

scan_container=db.create_container_if_not_exists(
    id="scan",
    partition_key=PartitionKey(path="/store_id")
)