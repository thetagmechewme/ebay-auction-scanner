#!/usr/bin/env python3

#TODO - time left low for auction sniping

from datetime import datetime
from ebaysdk.exception import ConnectionError
from ebaysdk.finding import Connection
import pygsheets

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
#sheet (obj) - Google Sheets object
#buyIndex (int) - Determines index for auctions to buy in Google Sheets
#cellNumber (int) - Cell to look in for date
#currentDate (datetime) - Current date time
#RowIndex (int) - Row index for Google Sheets
def removeExpiredAuctions(sheet, buyIndex, cellNumber, currentDate, rowIndex):
	worksheet = sheet[buyIndex]
	expiredAuctions = worksheet.range('I'+str(cellNumber)+':I'+str(cellNumber))
	auctionDate = str(expiredAuctions[0])
	if(len(auctionDate) > 25):
		replacementChars = "[<Cell'>]"
		for char in auctionDate:
			if char in replacementChars:
				auctionDate= auctionDate.replace(char, '')
		#Have to account for not removing any numbers due to date/time.
		auctionDate = auctionDate.replace('I'+ str(cellNumber), '').strip()
		cellNumber = cellNumber + 1
		if (datetime.strptime(auctionDate,'%Y-%m-%d %H:%M:%S') <= currentDate):
				worksheet.delete_rows(index, 1)
		rowIndex = rowIndex + 1

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
def scanAuctions(info, searchTerms, dataIndex, buyIndex, fromCountry, condition, buyNow, shipping, resell, priceLimit):
	currentDate = datetime.now()
	api = Connection(appid=' ', config_file=None)
	request = {"keywords": searchTerms, "outputSelector": "SellerInfo"}
	auction = api.execute('findItemsAdvanced', request)
	assert(auction.reply.ack == 'Success')
	assert(type(auction.reply.timestamp) == datetime)
	assert(type(auction.reply.searchResult.item) == list)
	auctions = auction.reply.searchResult.item
	assert(type(auction.dict()) == dict)
	auth = pygsheets.authorize(service_file=' ')
	sheet = auth.open('eBay')
	worksheet = sheet[dataIndex]
	dupeURL = ''
	print('Looping through ' + str(len(auctions)) +' '+ info + ' ' + str(currentDate))

	for item in auctions:
		itemName =  item.get('title')
		itemCountry = item.get('country')
		itemLocation = item.get('location')
		itemShippingType = item.shippingInfo.get('shippingType')
		itemCost = item.sellingStatus.get('convertedCurrentPrice').value
		itemBuyNow = item.listingInfo.get('listingType')
		itemStatus = item.sellingStatus.get('sellingState')
		itemConditionID = str(item.condition.get('conditionId'))
		itemCondition = conditionDef(str(item.condition.get('conditionId')))
		itemURL = item.get('viewItemURL')
		itemStart = str(item.listingInfo.get('startTime'))
		itemEnd = str(item.listingInfo.get('endTime'))
		sellerFeedbackscore = int(item.sellerInfo.get('feedbackScore'))
		sellerPositiveFeedback = float(item.sellerInfo.get('positiveFeedbackPercent'))

		listOfURLS = worksheet.find(itemURL)
		if(len(listOfURLS) == 1):
			dupeURL = str(listOfURLS[0])

		if(itemURL not in dupeURL and fromCountry in itemCountry and itemBuyNow == buyNow and itemConditionID in str(condition) and sellerFeedbackscore > 10 and sellerPositiveFeedback >= 90 and itemShippingType == 'Free'):
			if(resell):
				cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')
				lastRow = len(cells)
				worksheet.insert_rows(lastRow, number=1, values=[itemName, itemCountry, itemLocation, itemShippingType, itemBuyNow, itemStatus, itemURL, itemStart, itemEnd, itemCost])
			elif(not resell and float(itemCost) <= priceLimit):
				cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')
				lastRow = len(cells)
				worksheet.insert_rows(lastRow, number=1, values=[itemName, itemCountry, itemLocation, itemShippingType, itemBuyNow, itemStatus, itemURL, itemStart, itemEnd, itemCost])
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
			itemBuyNow = item.listingInfo.get('listingType')
			itemStatus = item.sellingStatus.get('sellingState')
			itemConditionID = str(item.condition.get('conditionId'))
			itemCondition = conditionDef(str(item.condition.get('conditionId')))
			itemURL = str(item.get('viewItemURL'))
			itemStart = str(item.listingInfo.get('startTime'))
			itemEnd = str(item.listingInfo.get('endTime'))
			sellerFeedbackscore = int(item.sellerInfo.get('feedbackScore'))		
			sellerPositiveFeedback = float(item.sellerInfo.get('positiveFeedbackPercent'))

			costBasis = avg if avg < median else median
			profit = (costBasis-itemCost)
			fees = (costBasis * .25) if shipping else (costBasis * .15)
			if(profit > fees):
				worksheet = sheet[buyIndex]
				listOfURLS = worksheet.find(itemURL)
				if(len(listOfURLS) == 1):
					dupeURL = str(listOfURLS[0])
				if(itemURL not in dupeURL and fromCountry in itemCountry and itemBuyNow == buyNow and itemConditionID in str(condition) and sellerFeedbackscore > 10 and sellerPositiveFeedback >= 90 and itemShippingType == 'Free'):
						cells = worksheet.get_all_values(include_tailing_empty_rows=False, include_tailing_empty=False, returnas='matrix')		
						lastRow = len(cells)
						worksheet.insert_rows(lastRow, number=1, values=[itemName, itemCountry, itemLocation, itemShippingType, itemBuyNow, itemStatus, itemURL, itemStart, itemEnd, itemCost, profit])

			removeExpiredAuctions(sheet, buyIndex, 2, currentDate, 2)
	else:
		removeExpiredAuctions(sheet, dataIndex, 2, currentDate,2)

#Resell Auctions Scanning

#Xbox Game Pass Ultimate
scanAuctions('Game Pass auctions', 'game pass ultimate trial', 0, 3, 'US', ['1000'], 'FixedPrice', False, True, 0.00)

#Xbox Series X
scanAuctions('XBSX auctions', 'xbox series x', 1, 4, 'US', ['1000'],'FixedPrice', True, True, 0.00)

#PS5
scanAuctions('PS5 auctions', 'playstation 5', 2, 5, 'US', ['1000'], 'FixedPrice', True, True, 0.00)


#Buying Auctions Scanning
scanAuctions('Resident Evil 8 Xbox', 'resident evil 8 xbox one', 6, 0, 'US',['2750','3000','4000','5000','1000','1500'], 'FixedPrice', False, False, 30.00)
