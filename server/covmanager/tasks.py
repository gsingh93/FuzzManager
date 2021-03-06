from django.conf import settings  # noqa

from celeryconf import app  # noqa


@app.task
def check_revision_update(pk):
    from covmanager.models import Collection, Repository  # noqa
    collection = Collection.objects.get(pk=pk)

    # Get the SourceCodeProvider associated with this collection
    provider = collection.repository.getInstance()

    # Check if the provider knows the specified revision
    if not provider.testRevision(collection.revision):
        # If not, update the repository
        provider.update()

    # TODO: We could double-check here that the revision is now known
    # and raise an error if not. This error would have to be propagated
    # to the user and since we already saved the collection, we can't
    # reject the client anymore.

    return
