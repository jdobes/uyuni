# Copyright (c) 2018 SUSE LLC
# Licensed under the terms of the MIT license.

Feature: Bootstrap a Salt minion via the GUI with an activation key

  Scenario: Delete SLES minion system profile
    Given I am on the Systems overview page of this "sle-minion"
    When I follow "Delete System"
    And I should see a "Confirm System Profile Deletion" text
    And I click on "Delete Profile"
    Then I wait until I see "has been deleted" text
    And I cleanup minion "sle-minion"

  Scenario: Create a configuration channel for the activation key
    Given I am authorized as "admin" with password "admin"
    When I follow "Home" in the left menu
    And I follow "Configuration" in the left menu
    And I follow "Configuration Channels" in the left menu
    And I follow "Create Config Channel"
    And I enter "Key Channel" as "cofName"
    And I enter "keychannel" as "cofLabel"
    And I enter "This is a configuration channel for the activation key" as "cofDescription"
    And I click on "Create Config Channel"
    Then I should see a "Key Channel" text

  Scenario: Add a configuration file to the key configuration channel
    Given I am authorized as "admin" with password "admin"
    When I follow "Home" in the left menu
    And I follow "Configuration" in the left menu
    And I follow "Configuration Channels" in the left menu
    And I follow "Key Channel"
    And I follow "Create Configuration File or Directory"
    And I enter "/etc/euler.conf" as "cffPath"
    And I enter "e^i.pi=-1" in the editor
    And I click on "Create Configuration File"

  Scenario: Create a complete minion activation key
    Given I am on the Systems page
    When I follow "Activation Keys" in the left menu
    And I follow "Create Key"
    And I enter "Minion testing" as "description"
    And I enter "MINION-TEST" as "key"
    And I enter "20" as "usageLimit"
    And I select "Test-Channel-x86_64" from "selectedChannel"
    And I click on "Create Activation Key"
    And I follow "Configuration" in the content area
    And I follow first "Subscribe to Channels" in the content area
    And I check "Key Channel" in the list
    And I click on "Continue"
    And I follow "Packages"
    And I enter "orion-dummy perseus-dummy" as "packages"
    And I click on "Update Activation Key"
    Then I should see a "Activation key Minion testing has been modified" text

  Scenario: Bootstrap a SLES minion with an activation key
    Given I am authorized
    When I go to the bootstrapping page
    Then I should see a "Bootstrap Minions" text
    When I enter the hostname of "sle-minion" as hostname
    And I enter "22" as "port"
    And I enter "root" as "user"
    And I enter "linux" as "password"
    And I select "1-MINION-TEST" from "activationKeys"
    And I select the hostname of the proxy from "proxies"
    And I click on "Bootstrap"
    Then I wait until I see "Successfully bootstrapped host! " text

  Scenario: Wait for minion to finish bootstrap
    Given I am authorized
    When I navigate to "rhn/systems/Overview.do" page
    And I wait until I see the name of "sle-minion", refreshing the page
    And I wait until onboarding is completed for "sle-minion"

  Scenario: Verify that minion bootstrapped with Salt key and packages
    Given I am authorized
    When I go to the minion onboarding page
    Then I should see a "accepted" text
    And the Salt master can reach "sle-minion"
    And I wait for "orion-dummy" to be installed on this "sle-minion"
    And I wait for "perseus-dummy" to be installed on this "sle-minion"
    And I remove package "orion-dummy" from this "sle-minion"
    And I remove package "perseus-dummy" from this "sle-minion"

  Scenario: Check system ID of bootstrapped minion
    Given I am on the Systems overview page of this "sle-minion"
    Then I run spacecmd listevents for "sle-minion"

  Scenario: Verify that minion bootstrapped with activation key
     Given I am on the Systems overview page of this "sle-minion"
     Then I should see a "Activation Key: 	1-MINION-TEST" text

  Scenario: Verify that minion bootstrapped with base channel
     Given I am on the Systems page
     Then I should see a "Test-Channel-x86_64" text

  # bsc#1080807 - Assigning configuration channel in activation key doesn't work
  Scenario: Verify that minion bootstrapped with configuration channel
    Given I am on the Systems overview page of this "sle-minion"
    When I follow "Configuration" in the content area
    Then I should see a "1 configuration channel" text
    When I follow "View Files" in the content area
    Then I should see a "/etc/euler.conf" text
    And I should see a "Key Channel" text

  Scenario: Cleanup: remove the key configuration channel
    Given I am authorized as "admin" with password "admin"
    When I follow "Home" in the left menu
    And I follow "Configuration" in the left menu
    And I follow "Configuration Channels" in the left menu
    And I follow "Key Channel"
    And I follow "Delete Channel"
    And I click on "Delete Config Channel"

  Scenario: Cleanup: delete the activation key
    Given I am on the Systems page
    And I follow "Activation Keys" in the left menu
    And I follow "Minion testing" in the content area
    And I follow "Delete Key"
    And I click on "Delete Activation Key"
    And I should see a "Activation key Minion testing has been deleted." text
