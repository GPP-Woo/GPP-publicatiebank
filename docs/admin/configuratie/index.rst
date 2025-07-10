.. _admin_configuratie_index:

Configuratie
============

Onder het menu-item "Configuratie" kan je diverse instellingen beheren die het gedrag
van het "woo-publicaties"-component beïnvloeden:

.. we don't document the remainder - through user groups/permissions we should only
   expose global configuration + services (maybe certificates if needed), so those items
   will not be visible anyway.

* Algemene instellingen
* Services

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_configuratie_index_alg_inst:

Algemene instellingen
---------------------

Toelichting
~~~~~~~~~~~

Omdat woo-publicaties gebruik maakt van de Documenten API uit de "API's voor
Zaakgericht Werken"-standaard zijn er een aantal aspecten die globaal ingesteld moeten
worden om gebruik te kunnen maken van deze API.

De voordelen van hergebruik binnen het API-landschap wegen (naar onze mening) op tegen
deze ongemakken.

Beheerscherm
~~~~~~~~~~~~

Het beheerscherm brengt je onmiddellijk naar het formulier om instellingen te bekijken
en aan te passen. Hier zien we:

* **Alle instellingen**. Deze lichten we hieronder toe.
* Rechtsboven een knop **Geschiedenis**. Deze toont de beheer-handelingen die vanuit de
  beheerinterface zijn uitgevoerd op de *algemene instellingen*.
* Linksonder de mogelijkheid om **wijzigingen op te slaan**. Er kan voor gekozen worden
  om na het opslaan direct de *instellingen* nogmaals te wijzigen.

De volgende instellingen zijn beschikbaar, waarbij verplichte velden **dikgedrukt**
worden weergegeven.

* ``Documenten API service``. Een keuzemenu om de relevante
  :ref:`service <admin_configuratie_index_services>` met verbindingsparameters te
  selecteren. Mits je de nodige rechten hebt kan je hier ook:

  - klikken op het potloodicoon om de service aan te passen
  - klikken op het plusicoon om een nieuwe service toe te voegen

  Deze instelling is noodzakelijk voor de verbinding met de achterliggende Documenten
  API.

* ``Organisatie-RSIN``. Het RSIN van de organisatie (in de praktijk: de gemeente) die
  de bronhouder is van de te publiceren documenten.

  .. warning:: Het is momenteel niet mogelijk om meerdere RSINs in te stellen in een
     instantie die voor meerdere gemeenten gebruikt wordt.

.. _admin_configuratie_index_services:

Services
--------

.. todo:: Aanvullen.
