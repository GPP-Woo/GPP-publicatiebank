.. _admin_logging_index:

Logging
=======

Onder het menu-item "Logging" en op het dashboard onder het kopje "Logging" wordt toegang geboden tot het beheer van:

* :ref:`admin_logging_index_auditlogitems`
* :ref:`admin_logging_index_accessattempts`
* :ref:`admin_logging_index_accessfailures`
* :ref:`admin_logging_index_accesslogs`
* :ref:`admin_logging_index_requestlogs`

Door hierop te klikken wordt het desbetreffende beheerscherm geopend.

.. _admin_logging_index_auditlogitems:

(audit)logitems
---------------
Hier wordt de logging getoond van:

* :ref:`admin_publicaties_index_publicaties`
* :ref:`admin_publicaties_index_documenten`
* :ref:`admin_publicaties_index_onderwerpen`
* :ref:`admin_metadata_index_information_categories`
* :ref:`admin_metadata_index_organisations`
* :ref:`admin_metadata_index_themes`
* :ref:`admin_accounts_index_users` (degene die direct toegang hebben tot dit component)
* :ref:`admin_accounts_index_employees`
* :ref:`admin_api_access_index_apikeys`

Daarop worden de volgende handelingen gelogd. 

* Nieuwe records (create)
* Raadplegingen van records (read)
* Downloaden van bestanden (bij _documenten_)
* Wijzigingen van records (update / patch)
* Verwijdering / vernietiging van records (delete)

Zowel handelingen uitgevoerd via de admin-interface als via de API worden gelogd.

Op het beheerscherm zijn de volgende acties mogelijk:

* Bovenaan zit een zoekveld met een knop **Zoeken** waarmee naar *(audit)logitems* gezocht kan worden.
* Onder de (bulk-)actie staat de lijst met *(audit)logitems*. Door op de kolomtitels (m.u.v. de kolom `bericht`) te klikken kan de lijst **alfabetisch of chronologisch geordend** worden.
* Rechts naast de lijst bestaat de mogelijkheid om deze te **filteren op datum en/of gebeurtenis**.
* Bij een *(audit)logitem* kan op het `bericht` geklikt worden om **de details in te zien**. Daarbij worden o.a. de gegevens getoond van het betrokken object zoals bekend direct ná de handeling.
* Bij een *(audit)logitem* kan op het **betrokken object** (rechter kolom) geklikt worden om direct naar het record te gaan waar het *(audit)logitem* betrekking op heeft.

.. _admin_logging_index_accessattempts:

Access attempts
---------------

GPP-publicatiebank heeft bescherming tegen het *brute-forcen* van inloggen met lokale
gebruikersaccounts. Als onderdeel daarvan worden inlogpogingen vastgelegd.

.. warning:: Dit onderdeel behoort tot de geavanceerde/technische functies en bevat
   mogelijk gegevens zoals IP-addressen en andere gegevens die tot een persoon
   te herleiden zijn.

.. _admin_logging_index_accessfailures:

Access failures
---------------

GPP-publicatiebank heeft bescherming tegen het *brute-forcen* van inloggen met lokale
gebruikersaccounts. Als onderdeel daarvan worden mislukte inlogpogingen vastgelegd.

.. warning:: Dit onderdeel behoort tot de geavanceerde/technische functies en bevat
   mogelijk gegevens zoals IP-addressen en andere gegevens die tot een persoon
   te herleiden zijn.

.. _admin_logging_index_accesslogs:

Access logs
-----------

GPP-publicatiebank heeft bescherming tegen het *brute-forcen* van inloggen met lokale
gebruikersaccounts. Als onderdeel daarvan worden geslaagde inlogpogingen vastgelegd,
ook als je met een organisatie-account inlogt.

.. warning:: Dit onderdeel behoort tot de geavanceerde/technische functies en bevat
   mogelijk gegevens zoals IP-addressen en andere gegevens die tot een persoon
   te herleiden zijn.

.. _admin_logging_index_requestlogs:

Uitgaande request-logs
----------------------

De GPP-publicatiebank koppelt zelf ook met achterliggende systemen. Wanneer het
netwerkverkeer naar deze system gelogd wordt, dan is dit hier in te zien.

.. warning:: Dit onderdeel behoort tot de geavanceerde/technische functies en bevat
   mogelijk gegevens zoals IP-addressen en andere gegevens die tot een persoon
   te herleiden zijn.
