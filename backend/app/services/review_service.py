from app.core.database import checkpoints_container
from datetime import datetime

class ReviewService:
    async def get_checkpoint(self, checkpoint_id: str):
        query = f"""
        SELECT *
        FROM c
        WHERE c.id = '{checkpoint_id}'
        """

        items = list(
            checkpoints_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
        )
        if not items:
            return None
        
        return items[0]


    async def get_review(self, checkpoint_id: str):
        return await self.get_checkpoint(checkpoint_id)

    async def deploy_checkpoint(self, checkpoint_id: str):
        checkpoint = await self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return None
        
        checkpoint["deployment_status"] = "deployed"
        checkpoint["is_active"] = True

        checkpoints_container.replace_item(
            item=checkpoint,
            body=checkpoint
        )
        return checkpoint

    
    async def cancel_checkpoint(self, checkpoint_id: str):
        checkpoint = await self.get_checkpoint(checkpoint_id)  
        if not checkpoint:
            return None

        checkpoint["deployment_status"] = "cancelled"
        checkpoint["is_active"] = False

        checkpoints_container.replace_item(
            item=checkpoint["id"],
            body=checkpoint
        )
        return checkpoint