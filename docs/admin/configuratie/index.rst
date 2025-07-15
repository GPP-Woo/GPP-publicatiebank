.. _admin_configuratie_index:

Configuratie
============

Onder het menu-item "Configuratie" kan je diverse instellingen beheren die het gedrag
van de GPP-publicatiebank beïnvloeden, waaronder:

.. we don't document the remainder - through user groups/permissions we should only
   expose global configuration + services (maybe certificates if needed), so those items
   will not be visible anyway.

* :ref:`admin_configuratie_index_alg_inst`
* :ref:`admin_configuratie_index_services`

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_configuratie_index_alg_inst:

Algemene instellingen
---------------------

Toelichting
~~~~~~~~~~~

Omdat de GPP-publicatiebank gebruik maakt van de Documenten API uit de "API's voor
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

* ``Organisatie-RSIN``. Het RSIN van de default organisatie (in de praktijk: de gemeente) die
  de bronhouder is van de te publiceren documenten. Deze wordt gebruikt wanneer op de :ref:`organisatie <admin_metadata_index_organisations>` geen RSIN is ingevuld.

* ``GPP-zoeken service``. Een keuzemenu om de relevante
  :ref:`service <admin_configuratie_index_services>` met verbindingsparameters te
  selecteren. Mits je de nodige rechten hebt kan je hier ook:

  - klikken op het potloodicoon om de service aan te passen
  - klikken op het plusicoon om een nieuwe service toe te voegen

  Deze instelling is noodzakelijk voor de verbinding met het GPP-zoeken-component (of passend alternatief).

* ``GPP-app publicatie-URL-sjabloon``. Het sjabloon waarmee op basis van het UUID de URL gegenereerd kan worden waarmee de :ref:`publicatie <admin_publicaties_index_publicaties>` te openen is in de GPP-app (of passend alternatief). Deze URL wordt live gegenereerd en opgenomen in de response na het aanroepen van de API (``urlPublicatieIntern``).

* ``GPP-burgerportaal publication-URL-sjabloon``. Het sjabloon waarmee op basis van het UUID de URL gegenereerd kan worden waarmee de :ref:`publicatie <admin_publicaties_index_publicaties>` te openen is in het GPP-burgerportaal (of passend alternatief). Deze URL wordt live gegenereerd en opgenomen in de response na het aanroepen van de API (``urlPublicatieExtern``).

.. _admin_configuratie_index_services:

Services
--------

.. todo:: Aanvullen.
