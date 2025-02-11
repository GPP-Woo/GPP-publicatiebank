.. _compliancy_api-strategy:

=======================
API strategy compliancy
=======================

The API is designed to adhere to API principles defined in `API Designrules`_, which is
a part of `Nederlandse API Strategie`_.

.. csv-table:: Adherence to API principles
   :header: "#", "Principle", "Compliant?"
   :widths: 10, 65, 25

   API-01,Operations are Safe and/or Idempotent,Yes
   API-02,Do not maintain state information at the server,Yes
   API-03,Only apply default HTTP operations,Yes
   API-04,Define interfaces in Dutch unless there is an official English glossary,Yes
   API-05,Use plural nouns to indicate resources,Yes
   API-06,Create relations of nested resources within the endpoint,N/a
   API-09,Implement custom representation if supported,Yes
   API-10,Implement operations that do not fit the CRUD model as sub-resources,Yes
   API-16,Use OAS 3.0 for documentation,Yes
   API-17,Publish documentation in Dutch unless there is existing documentation in English or there is an official English glossary available,Yes
   API-18,Include a deprecation schedule when publishing API changes,Yes
   API-19,Allow for a maximum 1 year transition period to a new API version,Yes
   API-20,Include the major version number only in ihe URI,Yes
   API-48,Leave off trailing slashes from API endpoints,Yes
   API-51,Publish OAS at the base-URI in JSON-format,Yes

.. _`API Designrules`: https://gitdocumentatie.logius.nl/publicatie/api/adr/
.. _`Nederlandse API Strategie`: https://docs.geostandaarden.nl/api/API-Strategie/
