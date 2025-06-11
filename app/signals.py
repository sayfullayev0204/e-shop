from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Transaction, Statistics

@receiver(post_save, sender=Transaction)
def update_statistics(sender, instance, created, **kwargs):
    """
    Update statistics when a transaction is created
    """
    if created and instance.transaction_type == 'OUT':
        # Get or create statistics for today
        today = timezone.now().date()
        stats, created = Statistics.objects.get_or_create(date=today)
        
        # Update statistics
        stats.total_sales += instance.quantity
        
        # Use sold_price from transaction instead of sale_price
        if instance.sold_price:
            stats.total_revenue += instance.quantity * instance.sold_price
        else:
            # Fallback to min_sale_price if sold_price is not set
            stats.total_revenue += instance.quantity * instance.product.min_sale_price
            
        stats.save()
