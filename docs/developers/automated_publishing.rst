.. _developers_automated_publishing:

==================================
Automation from 3rd party software
==================================

The :ref:`API endpoints <api_index>` from GPP-Publicatiebank enable other software
modules (like case management systems) to prepare publications to be made public on
the GPP-WOO stack.

.. note:: This is also documented in the `FAQ section on the website <https://www.gpp-woo.nl/faq>`_,
   see **Integratie** > **Kan ik mijn zaaksysteem, DMS of andere bron-applicatie ...**,
   which also contains some useful sequence diagrams.

Using the label "AppX" to denotate an external application, the flow can be summarized
as:

#. In AppX, a trigger initiates the publication process.
#. AppX creates a concept ``Publicatie`` resource via the GPP-Publicatiebank API. You
   receive the unique ID of this publicatie to relate other resources to.
#. For each document to publish, belonging to the publication:

    #. Create the ``Document`` metadata with the location of document in a
       "Documenten API", or:
    #. Upload the binary file content of the document.

#. Publish the publication, or point an end-user to the GPP-app to finalize the details
   and publish it.
#. GPP-Publicatiebank sends it to the search index and makes it available for citizens.

Prerequisites
=============

**API key and permissions**

A functional administrator of GPP-Publicatiebank must generate an API key for the
external application, and assign "read" and "write" permissions.

The API documentation provides details on how to use this key in API calls.

**Retrieving documents from an external Documents API**

If GPP-Publicatiebank needs to retrieve documents stored in an external Documents API,
then the credentials for this external API must be specified in the
:ref:`services <configuration_services>` configuration.

**Audit trail information**

The ``Audit-User-ID``, ``Audit-User-Representation`` and ``Audit-Remarks`` request
headers are usually mandatory. Based on these headers, the owner of a publication is
set, determined and checked.

In the external application, you should relay the metadata of the currently logged in
user in these headers so that there's an audit trail and ownership is correctly
organized. Note that the user ID is expected to be globally unique.

Creating a ``Publicatie``
=========================

API operation: ``publicatiesCreate``.

Some properties must point to existing metadata resources. The list below documents
these and where in the API you can find these:

* ``informatieCategorieen``: API operation ``informatiecategorieenList``
* ``onderwerpen``: API operation ``onderwerpenList``
* ``publisher``, ``verantwoordelijke`` and ``opsteller``: API operation ``organisatiesList``

When creating a concept publication, the only required attribute is to provide the
``officieleTitel``. Of course, any additional metadata you can already provide, reduces
the manual labour necessary to finish the publication.

The response data includes the property ``urlPublicatieIntern``, pointing to the
configured GPP-app. You can use this URL to show or direct the user to where they can
complete the publication process after creating a concept.

Adding ``Documents``
====================

API operation: ``documentenCreate``.

This operation registers the metadata of a document to be published and decides the
strategy on how the file data will be provided, through the ``aanleveringBestand``
property.

When ``ontvangen`` (upload to GPP-Publicatiebank) is selected, the response data contains
metadata about the expected file chunks. See the ``documentenBestandsdelenUpdate``
operation for additional details.

When ``ophalen`` (download from somewhere else) is selected, you must also provide the
``documentUrl`` where the file resource is available. This must point to an endpoint
that's compatible with the "Documenten API" VNG standard. GPP-publicatiebank figures
out the exact download URL automatically.

For the remaining metadata properties:

* ``publicatie``: use the ``uuid`` returned from the ``Publicatie`` resource created in
  the previous step.

Publish the ``Publicatie``
==========================

Using the ``urlPublicatieIntern`` from the initial creation, a user can navigate to the
GPP-app and perform the final checks. The user is only able to do so if they are known
as the ``eigenaar`` of the publication. If all is right, they can publish through the
UI.

Alternatively, you can incorporate the publish flow in your own software and set the
``publicatiestatus`` to ``gepubliceerd`` with a ``PATCH`` call.
