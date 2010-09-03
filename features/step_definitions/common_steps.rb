#
# Common "Then" phrases
#


#
# Test for a text in the whole page
#
Then /^I should see a "([^"]*)" text$/ do |arg1|
  page.should have_content(arg1)
end

#
# Test for a visible link in the whole page
#
Then /^I should see a "([^"]*)" link$/ do |arg1|
  find_link(arg1).visible?
end

#
# Test for a visible link inside of a <div> with the attribute 
# "class" or "id" of the given name
#
Then /^I should see a "([^"]*)" link in "([^"]*)"$/ do |arg1, arg2|
  within(:xpath, "//div[@id=\"#{arg2}\"] | //div[@class=\"#{arg2}\"]") do
    find_link(arg1).visible?
  end
end

#
# Test if a checkbox is checked
#
Then /^I should see "([^"]*)" as checked$/ do |arg1|
  has_checked_field?(arg1)
end

#
# Test the current path of the URL
#
Then /^the current path is "([^"]*)"$/ do |arg1|
  (current_path == arg1)
end


Then /^I should see "([^"]*)" in field "([^"]*)"$/ do |arg1, arg2|
  page.has_field?(arg2, :with => arg1)
end



#
# Common "When" phrases
#

#
# Check a checkbox of the given id
#
When /^I check "([^"]*)"$/ do |arg1|
  check(arg1)
end


When /^I select "([^"]*)"$/ do |arg1|
  pending # express the regexp above with the code you wish you had
end

#
# Enter a text into a textfield
#
When /^I enter "([^"]*)" as "([^"]*)"$/ do |arg1, arg2|
  fill_in arg2, :with => arg1
end

#
# Click on a button
#
When /^I click on "([^"]*)"$/ do |arg1|
  click_button arg1
  sleep(1)
end

#
# Click on a link
#
When /^I follow "([^"]*)"$/ do |arg1|
  find_link(arg1).click
  sleep(1)
end

#
# Click on a link which appears inside of <div> with 
# the given "id"
When /^I follow "([^"]*)" in "([^"]*)"$/ do |arg1, arg2|
  within(:xpath, "//div[@id=\"#{arg2}\"]") do
    find_link(arg1).click
  end
  sleep(1)
end

#
# Sleep for X seconds
#
When /^I wait for "(\d+)" seconds$/ do |arg1|
  sleep(arg1.to_i)
end



