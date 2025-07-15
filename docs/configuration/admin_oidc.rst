.. _configuration_admin_oidc:

OpenID Connect for the admin
============================

GPP-Publicatiebank supports Single Sign On (SSO) using OpenID Connect identity
providers. This means you can use your existing organisation account if you have
centralized account management, like Azure AD for example.

Using OIDC usually also enables you to automatically assign users to the appropriate
permission groups based on their roles managed in your Identity and Access Management
(AIM) solution.

Configuration of the OpenID Connect Identity Provider (OIP)
-----------------------------------------------------------

First, the IAM administrators in your organization must create a set of credentials
in your environment for GPP-Publicatiebank to use. Typically this requires them to
create a *Client* or an *App* in some administration portal.

This app needs to put the callback endpoint on an allowlist. Usually this is called
the **Redirect URI**. For its value, use:
``https://my-gpp-publicatiebank.example.com/auth/oidc/callback/``, where you replace
``my-gpp-publicatiebank.example.com`` name with your real/actual domain.

**Configuration parameters**

At the end of this process, the technical administrator for GPP-Publicatiebank must have
the following connection details:

* Client ID, for example ``a7d14516-8b20-418f-b34e-25f53c930948``
* Client secret, for example ``97d663a9-3624-4930-90c7-2b90635bd990``
* Discovery endpoint, for example
  ``https://login.microsoftonline.com/9c6a25fb-3f9a-4e8b-aa84-b7e2252bcc87/v2.0/``

Configuration of OpenID Connect in GPP-Publicatiebank
-----------------------------------------------------

Ensure that you have the discovery endpoint, client ID and secret as mentioned above.

Next, navigate to the **Admin** > **Configuratie** > **OpenID Connect Configuration**.

#. Check **Enable** to allow users to log in with SSO.
#. For **OpenID Connect client ID**, enter the obtained client ID, e.g.
   ``a7d14516-8b20-418f-b34e-25f53c930948``.
#. For **OpenID Connect secret**, enter the obtained secret, e.g.
   ``97d663a9-3624-4930-90c7-2b90635bd990``.
#. Usually you can keep the default values for the **OpenID Connect scopes**.
#. **OpenID sign algorithm** typically needs to be set to ``RS256``.
#. Leave **Sign key** blank.

Next, in the *Endpoints* section:

#. Enter the obtained **Discovery endpoint**. Make sure to *not* include the
   ``.well-known/openid-configuration`` part. For example:
   ``https://login.microsoftonline.com/9c6a25fb-3f9a-4e8b-aa84-b7e2252bcc87/v2.0/``

The discovery endpoint will be used to populate all the other endpoint parameters.

Finally, you can review the *User profile* section which configures synchronization
details for the users:

#. **Username claim** can typically be left as-is, unless instructed otherwise.
#. **Claim mapping** can be adapted if other claims than ``family_name`` and
   ``given_name`` are used by your OIP.
#. Check the **Make users staff** checkbox, otherwise they can't log in to the admin
   interface.
#. For the **Superuser group names** you can enter the role/group names in the ID token
   that mark a user as superuser (user that has all the permissions at all times), for
   example ``Superuser``.

Click the **Opslaan** button to save the configuration.

.. tip:: You can test the configuration by opening a private window and navigating to
   the admin login page. You should now see an option to "Log in with organisation account"
   and follow the login steps by clicking it.

Pre-configured groups
---------------------

A standard installation of GPP-publicatiebank comes with some
:ref:`user groups <admin_accounts_index_groups>` that permissions associated with them:

* ``TechnischBeheer``, intended for staff members that have to configure credentials to
  external services
* ``FunctioneelBeheer``, intended for staff members that know their way around the
  content managed in the application.

If these group names are present in the configured *Groups claim*, then user group
membership will be synced automatically.

.. tip::
   The permissions in the pre-configured groups are automatically updated every time the
   application is restarted. If you wish, you can create your own groups and add the
   group names to the user roles for automatic group assignment.
