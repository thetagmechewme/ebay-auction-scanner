#!/usr/bin/env python3

from datetime import datetime
from datetime import timedelta
from ebaysdk.exception import ConnectionError
from ebaysdk.finding import Connection
import pygsheets
import re
import time

def conditionsToWrite(itemURL, dupeURL, fromCountry, itemCountry, itemBuyNow, 
					itemConditionID, condition, sellerFeedbackscore, sellerPositiveFeedback, itemShippingType, acceptableShippingTypes, 
					itemEndTime, excludedKeywords, itemName):
	include = False
	emojis = re.findall(r'[^\w\s,(){}/\\-]', itemName)

	if(itemURL not in dupeURL and 
	fromCountry in itemCountry and 
	itemConditionID in str(condition) and 
	sellerFeedbackscore > 10 and 
	sellerPositiveFeedback >= 90 and 
	itemShippingType in str(acceptableShippingTypes) and
	itemBuyNow == 'FixedPrice' or itemBuyNow == 'StoreInventory'):
		include = True
		for emoji in emojis:
			for keyword in excludedKeywords:
				if keyword.upper() in itemName.upper() or (emoji + keyword.upper()) in itemName.upper() or (emoji + ' ' + keyword.upper()) in itemName.upper():
					include = False
					break

	return include
#Params
#conditionID (str) - Condition ID from eBay.
def conditionDef(conditionID):
	if(conditionID == '1000'):
		return 'New'
	elif(conditionID == '1500'):
		return 'New other (see details)'
	elif(conditionID == '1750'):
		return 'New with defects'
	elif(conditionID == '2000'):
		return 'Certified refurbished'
	elif(conditionID == '2500'):
		return 'Seller refurbished'
	elif(conditionID == '2750'):
		return 'Like New'	
	elif(conditionID == '3000'):
		return 'Used'
	elif(conditionID == '4000'):
		return 'Very Good'
	elif(conditionID == '5000'):
		return 'Good'
	elif(conditionID == '6000'):
		return 'Acceptable'
	elif(conditionID == '7000'):
		return 'For parts or not working'

#Params
#cell (obj) - Cell to be cleaned up
#cellLetter (str) - Cell letter to use as reference
def replaceChars(cell, cellLetter):
	if(len(cell) == 1):
		cellData = str(cell[0])
		replacementChars = "[<Cell" + cellLetter + "2'$>]"
		for char in cellData:
			if char in replacementChars:
				cellData = cellData.replace(char, '').strip()
		return float(cellData)


#Params
#Info (str) - Used for logging
#searchTerms (str) - Determines what auctions to search
#dataIndex (int) - Determines index for data training in Google Sheets
#buyIndex (int) - Determines index for auctions to buy in Google Sheets
#fromCountry (str) - Determines what country to look for auctions in
#condition (list) - Determines what condition of item to look for
#buyNow (str) - Determines what kind of auction to look at (ex. bidding vs buy it now)
#shipping (bool) - Determines if we need to ship an item or not (ex. digital item vs physical)
#resell (bool) - Determines if buying to resell or to have
#priceLimit (float) - Price limit for buying an auction to not resell
def scanAuctions(info, searchTerms, dataIndex, buyIndex, fromCountry, condition, shipping, resell, priceLimit, excludedKeywords =[]):
	try:
		currentDate = datetime.now()
		api = Connection(appid='APP_ID_HERE ', config_file=None)
		request = {"keywords": searchTerms, "outputSelector": "SellerInfo", "sortOrder": "PriceByShippingLowest"}
		auction = api.execute('findItemsAdvanced', request)
		assert(auction.reply.ack == 'Success')
		assert(type(auction.reply.timestamp) == datetime)
		assert(type(auction.reply.searchResult.item) == list)
		auctions = auction.reply.searchResult.item
		assert(type(auction.dict()) == dict)
		auth = pygsheets.authorize(service_file='JSON_AUTH_FILE_PATH')
		sheet = auth.open('eBay')
		worksheet = sheet[dataIndex]
		dupeURL = ''
		acceptableShippingTypes = ['Free', 'Fixed', 'FreightFlat', 'Flat']
		unacceptableShippingTypes = ['Calculated', 'CalculatedDomesticFlatInternational','CustomCode', 'Pickup', 'FreePickup', 'FlatDomesticCalculatedInternational', 'Free', 'NotSpecified']

		print('Looping through ' + str(len(auctions)) +' '+ info + ' ' + str(currentDate))

		for item in auctions:
			itemName =  item.get('title')
			itemCountry = item.get('country')
			itemLocation = item.get('location')
			itemShippingType = item.shippingInfo.get('shippingType')
			itemCost = float(item.sellingStatus.get('convertedCurrentPrice').value)
			if (itemShippingType not in str(unacceptableShippingTypes)):
				itemShippingCost = float(item.shippingInfo.shippingServiceCost.value)
			else:
				itemShippingCost = 0.0
			itemBuyNow = item.listingInfo.get('listingType')
			itemStatus = item.sellingStatus.get('sellingState')
			itemConditionID = str(item.condition.get('conditionId'))
			itemCondition = conditionDef(str(item.condition.get('conditionId')))
			itemURL = item.get('viewItemURL')
			itemStart = str(item.listingInfo.get('startTime'))
			itemEnd = str(item.listingInfo.get('endTime'))
			sellerFeedbackscore = int(item.sellerInfo.get('feedbackScore'))
			sellerPositiveFeedback = float(item.sellerInfo.get('positiveFeedbackPercent'))
			totalItemCost = itemCost + itemShippingCost

			listOfURLS = worksheet.find(itemURL)
			if(len(listOfURLS) == 1):
				dupeURL = str(listOfURLS[0])

			if(conditionsToWrite(itemURL, dupeURL, fromCountry, itemCountry, itemBuyNow,
						itemConditionID, condition, sellerFeedbackscore, sellerPositiveFeedback, itemShippingType, acceptableShippingTypes, 
						item.listingInfo.get('endTime'), excludedKeywords, itemName)):
				if(resell):
					cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')
					lastRow = len(cells)
					worksheet.insert_rows(lastRow, number=1, values=[itemName,
													  itemCountry,
													  itemLocation,
													  itemShippingType,
													  itemBuyNow,
													  itemStatus,
													  itemURL,
													  itemStart,
													  itemEnd,
													  totalItemCost])
				elif(not resell and float(totalItemCost) <= priceLimit):
					cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')
					lastRow = len(cells)
					worksheet.insert_rows(lastRow, number=1, values=[itemName,
													  itemCountry,
													  itemLocation,
													  itemShippingType,
													  itemBuyNow,
													  itemStatus,
													  itemURL,
													  itemStart,
													  itemEnd,
													  totalItemCost])
		if(resell):	
			#Cleans cell data up for parsing.
			avg = replaceChars(worksheet.range('L2:L2'), 'L')
			median = replaceChars(worksheet.range('M2:M2'), 'M')
		
			for item in auctions:
				itemName =  item.get('title')
				itemCountry = item.get('country')
				itemLocation = item.get('location')
				itemShippingType = item.shippingInfo.get('shippingType')
				itemCost = float(item.sellingStatus.get('convertedCurrentPrice').value)
				if (itemShippingType not in str(unacceptableShippingTypes)):
					itemShippingCost = float(item.shippingInfo.shippingServiceCost.value)
				else:
					itemShippingCost = 0.0
					itemBuyNow = item.listingInfo.get('listingType')
					itemStatus = item.sellingStatus.get('sellingState')
					itemConditionID = str(item.condition.get('conditionId'))
					itemCondition = conditionDef(str(item.condition.get('conditionId')))
					itemURL = str(item.get('viewItemURL'))
					itemStart = str(item.listingInfo.get('startTime'))
					itemEnd = str(item.listingInfo.get('endTime'))
					sellerFeedbackscore = int(item.sellerInfo.get('feedbackScore'))		
					sellerPositiveFeedback = float(item.sellerInfo.get('positiveFeedbackPercent'))
					totalItemCost = itemCost + itemShippingCost

				costBasis = avg if avg < median else median
				profit = (costBasis-totalItemCost)
				fees = (costBasis * .25) if shipping else (costBasis * .15)
				if(profit > fees and profit > totalItemCost - (totalItemCost * .20)):
					worksheet = sheet[buyIndex]
					listOfURLS = worksheet.find(itemURL)
					if(len(listOfURLS) == 1):
						dupeURL = str(listOfURLS[0])
					if(conditionsToWrite(itemURL, dupeURL, fromCountry, itemCountry, itemBuyNow,
						itemConditionID, condition, sellerFeedbackscore, sellerPositiveFeedback, itemShippingType, acceptableShippingTypes,
						item.listingInfo.get('endTime'), excludedKeywords, itemName)):
							cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')		
							lastRow = len(cells)
							worksheet.insert_rows(lastRow, number=1, values=[itemName,
														itemCountry,
														itemLocation,
														itemShippingType,
														itemBuyNow,
														itemStatus,
														itemURL,
														itemStart,
														itemEnd,
														totalItemCost,
														profit])
	except Exception as e:
		print(str(e))


#Clean up expired auctions

def cleanSheets(sheetIndex):
	try:
		currentDate = datetime.now()		
		auth = pygsheets.authorize(service_file='JSON_AUTH_FILE_PATH')
		sheet = auth.open('eBay')
		worksheet = sheet[sheetIndex]
		rows = worksheet.rows
		cellIndex = 0
		rowIndex = 2
		while rows > 0:
			expiredAuctions = worksheet.range('I'+str(cellIndex)+':I'+str(cellIndex))
			auctionDate = str(expiredAuctions[0])
			if(len(auctionDate) > 25):
					replacementChars = "[<Cell'>]"
					for char in auctionDate:
						if char in replacementChars:
							auctionDate= auctionDate.replace(char, '')
					#Have to account for not removing any numbers due to date/time.
					auctionDate = auctionDate.replace('I'+ str(cellIndex), '').strip()
					if (datetime.strptime(auctionDate,'%Y-%m-%d %H:%M:%S') < currentDate):
							worksheet.delete_rows(rowIndex, 1)
			cellIndex = cellIndex + 1
			rowIndex = rowIndex + 1
			rows = rows - 1
	except:
		cellIndex = cellIndex + 1
		rowIndex = rowIndex + 1
		rows = rows - 1
		pass

cleanSheets(0)
cleanSheets(1)
cleanSheets(2)
cleanSheets(3)
cleanSheets(4)
cleanSheets(5)
cleanSheets(6)

#Resell Auctions Scanning

#Xbox Game Pass Ultimate
scanAuctions('Game Pass auctions', 'game pass ultimate trial', 0, 3, 'US', ['1000'], False, True, 0.00)
time.sleep(10)

#Xbox Series X
scanAuctions('XBSX auctions', 'xbox series x', 1, 4, 'US', ['1000'], False, True, 0.00)
time.sleep(10)

#PS5
scanAuctions('PS5 auctions', 'playstation 5', 2, 5, 'US', ['1000'], False, True, 0.00)
time.sleep(10)

excludedSearchTerms = ['Loose','Replacement', 'Letter', 'Frame', 'Reward', 'Keychain', 'Steelbook', 'Cloud', 'Poster', 'Code', 'Memo', 'Shiny', 'Shirt', 'Bonus']

#Buying Auctions Scanning
scanAuctions('Red Dead Redemption 2 Xbox', 'red dead redepmtion 2 xbox one', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'],  False, False, 30.00, excludedSearchTerms)
time.sleep(10)

scanAuctions('Resident Evil 8 Xbox', 'resident evil 8 xbox one', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'],  False, False, 30.00, excludedSearchTerms)
time.sleep(10)

scanAuctions('New Pokemon Snap Switch', 'new pokemon snap switch', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
time.sleep(10)

scanAuctions('Splatoon 2 Switch', 'splatoon 2 switch', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
time.sleep(10)

scanAuctions('Pokemon Shield Switch', 'pokemon shield switch', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
time.sleep(10)

scanAuctions('Hyrule Warriors Age of Calamity', 'age of calamity switch', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
time.sleep(10)

scanAuctions('Luigis Mansion 3', 'luigis mansion 3 switch', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
time.sleep(10)

#scanAuctions('Starcraft 64', 'starcraft nintendo 64', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
#time.sleep(10)

#scanAuctions('Resident Evil 2 64', 'resident evil 2 nintendo 64', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], False, False, 30.00, excludedSearchTerms)
#time.sleep(10)

#scanAuctions('Roomba 675', 'irobot roomba 675', 6, 0, 'US',['1000'], False, False, 100.00)
#time.sleep(10)