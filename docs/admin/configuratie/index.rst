.. _admin_configuratie_index:

Configuratie
============

Onder het menu-item "Configuratie" kan je diverse instellingen beheren die het gedrag
van de GPP-publicatiebank beïnvloeden, waaronder:

.. we don't document the remainder - through user groups/permissions we should only
   expose global configuration + services (maybe certificates if needed), so those items
   will not be visible anyway.

.. contents:: Inhoud
   :backlinks: none
   :depth: 1
   :local:

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

* ``Strip documenten metadata``. Vlag die aangeeft of de documenten ge stripped moet worden van hun metadata, hier mee kan je er voor zorgen dat burgers niet kunnen achterhalen wie het document gemaakt heeft.

* ``Catalogi API service``. Een keuzemenu om de relevante
  :ref:`service <admin_configuratie_index_services>` met verbindingsparameters te
  selecteren. Mits je de nodige rechten hebt kan je hier ook:

  - klikken op het potloodicoon om de service aan te passen
  - klikken op het plusicoon om een nieuwe service toe te voegen

  Deze instelling is noodzakelijk voor de verbinding met de achterliggende Catalogi
  API. Die gebruikt wordt om documenten in de Documenten API te verzien van een Informatie Object typen (IOT).

  Wanneer dit veld ingevuld wordt (terwijl de `Catalogus URL` en/of de `Default Informatieobjecttype URL` leeg is) vullen wij onder water
  de `Catalogus URL` en de `Default Informatieobjecttype URL` in. Als deze velden successful aangemaakt en ingevuld wordt, gaan we verder door om
  de :ref:`informatiecategorie <admin_metadata_index_information_categories>` te voorzien van `Informatie Object Typen` vanuit de catalogi API, en
  zorgen we er voor dat alle Documenten in de `Documenten API` worden overschreven met de nieuwe `Informatie Object Typen` waardes.

* ``Catalogus URL``. Het URL van het Catalogus object van de geconfigureerde `Catalogus API service`.

  Dit veld wordt automatisch ingevuld wanneer de `Catalogi API service` geconfigureerd wordt (als dit veld leeg is of gemaakt wordt), als de `Catalogi`
  al eerder op deze methode is aangemaakt in de geconfigureerde `Catalogi API` dan zou u het manueel moeten invullen.

* ``Standaard Informatieobjecttypen URL``. Het URL van de `Informatie Object Typen` die gebruikt moet worden als een :ref:`publicatie <admin_publicaties_index_publicaties>`
  nog niet voorziet van een :ref:`informatiecategorie <admin_metadata_index_information_categories>`. De `Informatie Object Typen` zijn namelijk verplicht in de Documenten API
  voor de `Enkelvoudig Informatie Objecten` objecten die wij gebruiken om `Documenten` te bewaren.

  Dit veld wordt automatisch ingevuld wanneer de `Catalogi API service` geconfigureerd wordt (als dit veld leeg is of gemaakt wordt), als de `Catalogi`
  al eerder op deze methode is aangemaakt in de geconfigureerde `Catalogi API` dan zou u het manueel moeten invullen.

* ``GPP-app publicatie-URL-sjabloon``. Het sjabloon waarmee op basis van het UUID de URL gegenereerd kan worden waarmee de :ref:`publicatie <admin_publicaties_index_publicaties>` te openen is in de GPP-app (of passend alternatief). Deze URL wordt live gegenereerd en opgenomen in de response na het aanroepen van de API (``urlPublicatieIntern``).

* ``GPP-burgerportaal publication-URL-sjabloon``. Het sjabloon waarmee op basis van het UUID de URL gegenereerd kan worden waarmee de :ref:`publicatie <admin_publicaties_index_publicaties>` te openen is in het GPP-burgerportaal (of passend alternatief). Deze URL wordt live gegenereerd en opgenomen in de response na het aanroepen van de API (``urlPublicatieExtern``).

* ``Zienswijze reactie form URL``. Dit is de standaard URL voor het `reactieformulier` binnen de :ref:`inzage procedure <admin_publicaties_index_inzage_procedure>` wanneer `Beschikbaar rechtsmiddel` de waarde `zienswijze` heeft.

* ``Bezwaar reactie form URL``. Dit is de standaard URL voor het `reactieformulier` binnen de :ref:`inzage procedure <admin_publicaties_index_inzage_procedure>` wanneer `Beschikbaar rechtsmiddel` de waarde `bezwaar` heeft.


.. _admin_configuratie_index_applicatiegroepen:

Applicatiegroepen
-----------------

Applicatiegroepen worden gebruikt om de menustructuur te beheren. Je kan deze niet
aanpassen - aanpassingen worden bij het herstarten van de applicatie op de server
teruggedraaid.

.. _admin_configuratie_index_certificates:

Certificates
------------

.. note:: Certificaatbeheer is voor de GPP-Publicatiebank niet relevant.

.. _admin_configuratie_index_NLX_configuration:

NLX configuration
-----------------

.. note:: NLX-instellingen zijn voor de GPP-Publicatiebank niet relevant.

.. _admin_configuratie_index_services:

Services
--------

Onder "Services" kan je de connectie-parameters met externe services/API's instellen,
zoals Documenten API's en GPP-Zoeken. Zie :ref:`configuration_services` voor de
services die GPP-Publicatiebank nodig heeft.

.. _admin_configuratie_index_uitgaande_request_logging_configuratie:

Uitgaande request-logging configuratie
--------------------------------------

GPP-Publicatiebank maakt gebruik van externe API's om gegevens op te halen en op te
slaan. Via uitgaande request-logging kunnen fouten in dit netwerkverkeer onderzocht
worden.

.. warning::

  Standaard staat het loggen van netwerkverkeer uit. Loggen van uitgaand verkeer is van
  nature gevoelig, deze instellingen resetten dan ook automatisch na verloop van tijd.
  Schakel dit alleen in als je specifieke problemen aan het onderzoeken bent.

Beheerscherm
~~~~~~~~~~~~

Het beheerscherm gaat meteen naar de log-instellingen, waar de volgende velden
beschikbaar zijn:

* ``Logs opslaan in de database``. Stel expliciet in of uitgaande verzoeken in de
  databank moeten opgeslagen worden ("Ja") of dat hiervoor de server-instellingen
  gebruikt moeten worden ("Gebruik standaardconfiguratie").
* ``Sla de inhoud van request en/of response op in de database``. Maak een keuze om
  naast de metadata van een verzoek/antwoord ook de inhoud op te slaan.
* ``Maximale content-grootte``. Berichtinhoud die groter is dan deze instelling (in
  bytes) wordt niet opgeslagen. Dit is een veiligheidsmechanisme.
* ``Reset opslaan van logs in de database``. Gebruik een aangepaste timing dan de
  server-instelling voor het automatisch herstellen van de configuratie, in aantal
  minuten. Na deze tijd wordt de configuratie teruggezet en aanpassingen ongedaan
  gemaakt.
