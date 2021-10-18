2# Continue vessel model implementation 
# -*- coding: utf-8 -*-

#Created on Wed July 14 12:30 2021
#Author: Carloline Lueders


###############################################################################
import sys
import os
import numpy as np 
import json
import mesh
from datetime import datetime

def getModel(projectname):  

    #sourcepath=os.getcwd()
    #projectname=getInput('Geben Sie den Projektnamen ein:',default='test')
    #projectpath=sourcepath+'////'+projectname
    #os.chdir(projectpath)
    #filename=os.listdir(projectpath) 

    modelname=projectname
    global model
    model = mdb.models[modelname]    
    global parts
    parts = model.parts
    global assembly
    assembly = model.rootAssembly

def getInnerDomeContour(ys, xs, linerthickness, rzylinder):

#   generates the inner dome conture form the given outer dome contur
#   inner dome contour created by constant distance (thickness) from 
#   outer contur
#
#   returns x and y values of inner dome/liner contour
#
#   ys              : array of y values of outer liner contur
#   xs              : array of x values of outer liner contur
#   linerthickess   : desired thickness of liner
#   rzylinder       : radius in cylindrical regime (outer side of liner = inner side of winding)

    xs_inner = list()
    ys_inner = list()

    for i in range(len(ys)):
        x0 = xs[i]
        y0 = ys[i]

        print(x0, y0)
        
        if x0 == rzylinder: # if position is on krempe/cylinder
            xs_inner.append(x0-linerthickness)
            ys_inner.append(y0)                                  
        else:

            # calculate tangent slope in (y0,x0) / dy/dx
            if i == 1: # use forward difference equations
                print('first data point')
                if (ys[i+1]-y0) == 0.:
                    tangent_slope = float('inf')
                else:   
                    tangent_slope = (xs[i+1]-x0) / (ys[i+1]-y0)
            elif i == len(ys)-1: # usee backward difference equations
                print('last data point')
                if (ys[i-1]-y0)  == 0.:
                    tangent_slope = float('inf')
                else:
                    tangent_slope = (xs[i-1]-x0) / (ys[i-1]-y0)                

            else: # use central difference equations            
                if (ys[i+1]-ys[i-1]) == 0.:
                    tangent_slope = float('inf')
                else:
                    tangent_slope = (xs[i+1]-xs[i-1]) / (ys[i+1]-ys[i-1])                 

            # get point on inner liner contour
            if tangent_slope == 0: # this is in cylidnrical regime
                xs_inner.append(x0-linerthickness)
                ys_inner.append(y0)
            elif tangent_slope == float('inf'): # this is exact at polar opening
                xs_inner.append(x0)
                ys_inner.append(y0-linerthickness)
            else: # this is in dome regime
                # get point on contour normal that is linerthickness away from current point
                # (y0, x0); there are tow points -- one outsinde, one inside the liner
                # so firts solve pq-euaqtion to obtain corresponding y-avlues
                #yinner_1 = y0 + np.sqrt(y0**2. - (y0**2. - linerthickness**2. * tangent_slope**2.0) )
                #yinner_2 = y0 - np.sqrt(y0**2. - (y0**2. - linerthickness**2. * tangent_slope**2.0) )

                # get corresponding x-values (dome radius)
                #xinner_1 = (-1./tangent_slope)*yinner_1 + x0 + y0/tangent_slope
                #xinner_2 = (-1./tangent_slope)*yinner_2 + x0 + y0/tangent_slope

                # choose point lying within the vessel
                #if xinner_1 < x0:
                #    xs_inner = list(xs_inner)+list([xinner_1])   
                #    ys_inner = list(ys_inner)+list([yinner_1])   
                #else:
                #    xs_inner = list(xs_inner)+list([xinner_2])    
                #    ys_inner = list(ys_inner)+list([yinner_2])  

                xinner =x0-linerthickness*np.sin(np.arctan(-1.0/tangent_slope))
                xs_inner.append(xinner) 
                ys_inner.append(-tangent_slope*xinner+y0+x0*tangent_slope)                    

    return xs_inner, ys_inner


def getDomeContourFromFile(domefilename, rzylinder, lzylinder, linerthickness):

#   reads and returns x,y-values of liner contour
#
#   return contour: [x-values,y-values]; x = radius-position, y = position on tank axis
#   return sheetSize: estimated sheet size for liner sketch
#
#   input domefilename  : name of txt-file including datapoints of outer liner contour
#   input rzylinder     : radius in cylindrical regime (outer side of liner = inner side of winding)
#   input lzylinder     : length of cylincrical regime of tank
#   input linerthickess   : desired thickness of liner
#
    
    filename = open(domefilename,"r") 
    print ('Read dome contour from ', domefilename)
    Data = np.loadtxt(filename)  
    filename.close()   

    ys = abs(Data[:, 0])-abs(Data[0,0])+lzylinder/2. # positiona long axis
    xs = abs(Data[:,1]) # position dome radius
    dy = abs(max(ys)-min(ys))
    dx = abs(max(xs)-min(xs))
    sheetSize = max(dy, dx)

    xs_inner, ys_inner = getInnerDomeContour(ys, xs, linerthickness, rzylinder)

    xs_inner_rev = list(xs_inner)    
    xs_inner_rev.reverse()

    ys_inner_rev = list(ys_inner)
    ys_inner_rev.reverse()  

    ys = np.array(list([0.0] + list(ys) + ys_inner_rev + list([0.0]) ))
    xs = np.array(list([rzylinder] + list(xs) + xs_inner_rev + list([rzylinder-linerthickness]) ))
    
    
    contour = tuple((x,y) for x,y in zip(xs,ys))      

    return contour, sheetSize


def loadDomeContourToSketch(domefilename, rzylinder, lzylinder, linerthickness):

#   loads dome contour from file into Abaqus-Sketch
#
#   return: none
#
#   input domefilename  : name of txt-file including datapoints of outer liner contour
#   input rzylinder     : radius in cylindrical regime (outer side of liner = inner side of winding)
#   input lzylinder     : length of cylincrical regime of tank
#   input linerthickess   : desired thickness of liner
#
    contourpoints, sheet = getDomeContourFromFile(domefilename, rzylinder, lzylinder, linerthickness)  

    s1 = model.ConstrainedSketch(name='Liner', sheetSize=sheet)  
    s1.Spline(points = contourpoints)
    s1.Line(point1 = (rzylinder-linerthickness, 0.0), point2 = (rzylinder, 0.0))

def getPropsFromJson(materialPath, materialName):

# reads material props from json file
#
#   return props : array of prop values
#
#   input materialPath  : json-file (whole file path)
#   input materialName  : name of material for wich paramaters are to be read
    
    with open(materialPath,'r') as file:
        materialJson = json.loads(file.read())   

    for materialnr in materialJson["materials"]:

        if materialJson["materials"][str(materialnr)]["name"] == materialName:
            print('found material', materialJson["materials"][str(materialnr)]["name"])

            nTemps = materialJson["materials"][str(materialnr)]["umatProperties"]["number_of_temperatures"]            
            
            props = np.empty(0)
            print(props)
            
            for temp in range(1, nTemps+1):
                
                Temp = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["Temp"]                

                E11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["E_1"]
                E22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["E_2"]
                E33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["E_3"]
                G23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["G_23"]
                G13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["G_13"]
                G12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["G_12"]
                nu23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["nu_23"]
                nu13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["nu_13"]            
                nu12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["nu_12"]     
                eta = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatElasticProperties"]["eta"]     
                Xt = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_1_t"]     
                Xc = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_1_c"]     
                Yt = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_2_t"]     
                Yc = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_2_c"]     
                S12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["umatPuckProperties"]["R_21"]     
            
                beta_2_11t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_11t"]    
                beta_2_11c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_11c"]  
                beta_2_22t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_22t"]
                beta_2_22c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_22c"]
                beta_2_33t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_33t"]
                beta_2_33c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_33c"]
                beta_2_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_12"]
                beta_2_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_13"]
                beta_2_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_2_23"]
                beta_1_11t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_11t"]
                beta_1_11c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_11c"]
                beta_1_22t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_22t"]
                beta_1_22c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_22c"]
                beta_1_33t = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_33t"]
                beta_1_33c = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_33c"]
                beta_1_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_12"]
                beta_1_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_13"]
                beta_1_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["beta_1_23"]
                lambda_1_11 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_11"]
                lambda_1_22 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_22"]
                lambda_1_33 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_33"]
                lambda_1_12 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_12"]
                lambda_1_13 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_13"]
                lambda_1_23 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_1_23"]
                lambda_2_11 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_11"]
                lambda_2_22 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_22"]
                lambda_2_33 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_33"]
                lambda_2_12 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_12"]
                lambda_2_13 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_13"]
                lambda_2_23 =materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["lambda_2_23"]
                A_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_11"]
                B_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_11"]
                A_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_22"]
                B_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_22"]
                A_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_33"]
                B_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_33"]
                A_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_12"]
                B_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_12"]
                A_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_13"]
                B_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_13"]
                A_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["A_23"]
                B_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["B_23"]
                u_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_11"]
                u_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_22"]
                u_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_33"]
                u_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_12"]
                u_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_13"]
                u_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["u_23"]
                v_11 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_11"]
                v_22 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_22"]
                v_33 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_33"]
                v_12 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_12"]
                v_13 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_13"]
                v_23 = materialJson["materials"][str(materialnr)]["umatProperties"]["data_sets"][str(temp)]["fatigueProperties"]["v_23"]


                print('eta', eta)

                props = np.append(props, [E11, E22, E33, G12, G13, G23, nu12, nu13, nu23, Xt, Yt, Yt, Xc, Yc, Yc, S12, S12, S12, beta_2_11t, beta_2_11c, beta_2_22t, beta_2_22c, 
                beta_2_33t, beta_2_33c, beta_2_12 , beta_2_13 , beta_2_23 , beta_1_11t, beta_1_11c, beta_1_22t, beta_1_22c, beta_1_33t, beta_1_33c, beta_1_12 , beta_1_13 , beta_1_23 , 
                lambda_1_11, lambda_1_22, lambda_1_33, lambda_1_12, lambda_1_13, lambda_1_23, lambda_2_11, lambda_2_22, lambda_2_33, lambda_2_12, lambda_2_13, lambda_2_23, A_11, B_11, A_22, 
                B_22, A_33, B_33, A_12, B_12, A_13, B_13, A_23, B_23, eta, u_11, u_22, u_33, u_12, u_13, u_23, v_11, v_22, v_33, v_12, v_13, v_23, Temp])
                
                
                #props.extend([E11, E22, E33, G12, G13, G23, nu12, nu13, nu23, Xt, Yt, Yt, Xc, Yc, Yc, S12, S12, S12, beta_2_11t, beta_2_11c, beta_2_22t, beta_2_22c, 
                #beta_2_33t, beta_2_33c, beta_2_12 , beta_2_13 , beta_2_23 , beta_1_11t, beta_1_11c, beta_1_22t, beta_1_22c, beta_1_33t, beta_1_33c, beta_1_12 , beta_1_13 , beta_1_23 , 
                #lambda_1_11, lambda_1_22, lambda_1_33, lambda_1_12, lambda_1_13, lambda_1_23, lambda_2_11, lambda_2_22, lambda_2_33, lambda_2_12, lambda_2_13, lambda_2_23, A_11, B_11, A_22, 
                #B_22, A_33, B_33, A_12, B_12, A_13, B_13, A_23, B_23, eta, u_11, u_22, u_33, u_12, u_13, u_23, v_11, v_22, v_33, v_12, v_13, v_23, Temp])

    print(props)    

    return props

def getNumberOfLayerParts(layerPartPrefix):

# returns number of parts with names beginning with "layerPartPrefix"    
#
#   return nLayerParts  : numer of parts [int]
#
#   input layerPartPrefix   : name prefix of parts to be counted

    #parts = model.parts
    nParts = len(parts)
    
    nLayerParts = 0    
    for p in range(nParts):        
        try:
            layerpart = parts[layerPartPrefix+"_"+str(p)]
            nLayerParts = nLayerParts+1
        except:
            print("maximum number of parts beginnung with "+layerPartPrefix+" is found to be "+str(nLayerParts))

    return nLayerParts

def createUMATmaterials(model, layerMaterialPrefix, UMATprefix, materialPath, materialName, nDepvar, degr_fac, AbqMATinAcuteTriangles):

#   create material card for UMAT from material props from given json file
#
#   input layerMaterialPrefix : prefix used in material name for layer materials, e.g. "Layer_"
#   inout materialPath  : json-file (whole file path)
#   input materialName  : name of material for wich paramaters are to be read

    print("*** START GENERATE UMAT MATERIAL CARDS ***")  

    materials = model.materials    
    sections = model.sections
    materialProps = getPropsFromJson(materialPath, materialName)
    print('props', materialProps)

    print("*** GENERATE UMAT MATERIAL CARDS ***")    
        
    for key in materials.keys():        
        #print('key', key)
        if (key[0:len(layerMaterialPrefix)] == layerMaterialPrefix) or (key[13:13+len(layerMaterialPrefix)] == layerMaterialPrefix):            
            material = materials[key]            
            propsTemp = materialProps.copy()
            if not key[0:len(UMATprefix)] == UMATprefix and len(UMATprefix)>0:
                newKey = UMATprefix+'_'+key
                sectionkey = key
            else:
                newKey = key  
                sectionkey = newKey[13:len(newKey)]

            #print('nexKey', newKey)
            #print('sectionKEy', sectionkey)

            #get band angle from material description
            materialDescription= material.description
            if 'Mean Angle' in materialDescription: # for Models generated from muWind
                keyword = 'Mean Angle: '
                before_keyword, keyword, after_keyword = materialDescription.partition(keyword)            
                keyword = 'Clairault'
                before_keyword, keyword, after_keyword = after_keyword.partition(keyword)                
                angle_str = before_keyword.replace(',', '')
                angle = float(angle_str)      
            elif 'Beta' in materialDescription: # for models generated from WoundCompositeModeller
                keyword = 'Beta = '
                before_keyword, keyword, after_keyword = materialDescription.partition(keyword)
                keyword = ' ****'
                before_keyword, keyword, after_keyword = after_keyword.partition(keyword)
                angle_str = before_keyword
                #print(angle_str)
                angle = float(angle_str)   
            
            # append angle and degradation factor to props
            propsTemp = np.append(propsTemp, [angle])
            propsTemp = np.append(propsTemp, [degr_fac])
                                    
            try:
                del material.userMaterial
                material.UserMaterial(mechanicalConstants = propsTemp)

            except:
                print('no UMAT, will be created')
                material.UserMaterial(mechanicalConstants = propsTemp)                        
            try: 
                del material.depvar
                material.Depvar(n=nDepvar)              
            except:
                print('no UMAT, will be created')
                material.Depvar(n=nDepvar)  

            try:     
                del material.elastic
            except:
                print('Elastic Props already deleted')           

# ---------- rename material to trigger UMAT     
            if len(UMATprefix) > 0:           
                materials.changeKey(fromName=key, toName=newKey)
                sections[sectionkey].setValues(material=newKey, thickness=None)           
            
            if AbqMATinAcuteTriangles:
                setABQUMATinAcuteTriangles(sectionkey)

def setABQUMATinAcuteTriangles(sectionkey):             
    

def getAngleBetweenEdges(edges, partVertices):

# calculates the angle between given edges in Abaqus Model
#
#   return: angle between edges in degree
#
#   input   edges           : list/array of edge objects
#   input   partVertices    : all vertices of the part the edges belongs to

    slopes = []

    for edge in edges:
        EdgeVerticesIDs = edge.getVertices()     
        x0 = partVertices[EdgeVerticesIDs[0]].pointOn[0][0]
        y0 = partVertices[EdgeVerticesIDs[0]].pointOn[0][1]
        z0 = partVertices[EdgeVerticesIDs[0]].pointOn[0][2]
        x1 = partVertices[EdgeVerticesIDs[1]].pointOn[0][0]
        y1 = partVertices[EdgeVerticesIDs[1]].pointOn[0][1]
        z1 = partVertices[EdgeVerticesIDs[1]].pointOn[0][2]

        # consider only edges lying in xy-plane
        if (z0, z1) == (0., 0.):
            xmin = min(x0,x1)
            ymin = min(y0,y1)
            xmax = max(x0,x1)
            ymax = max(y0,y1)

            slopes.append((xmax-xmin)/(ymax-ymin))

    alpha = np.arctan(abs((slopes[0]-slopes[1])/(1+slopes[0]*slopes[1])))

    return (alpha*180)/np.pi

def seedLayerThicknessEdges(layerPartPrefix, elementsPerLayerThickness, minAngle):

#   sets mesh seeds at the leyer edges which represent the layer thickness
#   sets wedge elements for regions which are limited by edges with very small angles (e.g. narrow ends of layers)
#
#   return  none
#
# input layerPartPrefix             : name prefix of layer parts
# input elementsPerLayerThickness   : numer of elements desired per layer thickness, integer
# input minAngle                    : minimum anlge for using hex elements (for regions with lower angles, wedge elements are set)



    #parts = model.parts

    # define set in layer thickness direction that can be seeded later
    for p in range(len(parts)): #      

        try:
            part = parts[layerPartPrefix+'_'+str(p)] 
            layerPart = True
            print(layerPartPrefix+'_'+str(p)) 
        
        except KeyError:
            print('This is no Layer part') 
            layerPart = False      

        if layerPart == True:
            # get geometry entities
            partEdges = part.edges
            partVertices = part.vertices
            partGeometry = part.queryGeometry(printResults = False)

            # clear 
            part.deleteMesh()
            axialBottomEdge = partEdges.getByBoundingBox(-10000., -10000., -0.01, 10000., 10000., 0.01, )  
            part.deleteSeeds(regions=(axialBottomEdge, ))
            
            # get geonetric expanion of part // min and max coordinates
            boundingBoxMax = partGeometry["boundingBox"][1]
            maxVertexY = boundingBoxMax[1]

            # get vertex at dome wich is at the outer geometry position of part
            maxVertex = partVertices.getByBoundingBox(-10000., maxVertexY-0.01, -0.01, 10000., maxVertexY+0.01, 0.01)                        
            # create Set to get the vertices as vertex not as vertex array
            part.Set(name = 'MaxVertex', vertices = (maxVertex,))
            maxVertex = part.sets['MaxVertex'].vertices[0]
                        
            # edges of dome are adjacent edges of vertex at dome
            # obtain angle between them to decide mesh control options
            domeEdgesIDs = maxVertex.getEdges()   
            # create sequence with all edges
            domeEdges = (partEdges[domeEdgesIDs[0]],)
            for domeEdgeID in domeEdgesIDs[1:]:
                domeEdges = domeEdges+(partEdges[domeEdgeID], )                        
            alpha = getAngleBetweenEdges(domeEdges, partVertices)
            print(alpha)

            if alpha < minAngle:
                domeCell = part.cells.findAt((maxVertex.pointOn[0]), )                   
                part.setMeshControls(regions=(domeCell, ), elemShape=mesh.WEDGE)
           
            thicknessEdge = partEdges.getByBoundingCylinder((-10000.,0.,0.),(10000.,0.,0.),0.01)                        
            part.seedEdgeByNumber(edges = thicknessEdge, number = elementsPerLayerThickness, constraint = FIXED)
            part.generateMesh()
    

def reMeshVessel(elementsPerLayerThickness, layerPartPrefix, minAngle):

#   remesh the vessel with given mesh options
#
#   return   none
#
# input layerPartPrefix             : name prefix of layer parts
# input elementsPerLayerThickness   : numer of elements desired per layer thickness, integer
# input minAngle                    : minimum anlge for using hex elements (for regions with lower angles, wedge elements are set)
    
    seedLayerThicknessEdges(layerPartPrefix, int(elementsPerLayerThickness), minAngle)

#def createCorrespondingCSYS(setName1, setName2, partname):
#
#    # create face from points/nodes from sets
#    # create normals on that faces
#
#    
#
#    return csys1, csys2

def createPeriodicEquation(setName1, setName2, partname, instancePrefix, reveloveAngle, exceptionSetNodeLables):

#   creates periodic boundary equations between nodes in the given node sets (name given)
#   return  :   none
#
#   input   setName1, setName2 [string]   : names of node sets; setname1 should nbe face on xy-Plane (all z=0)
#           partname [string]             : name/key of part the sets belong to  
#           reveloveAngle [float]         : revelove angle of solid model
#           exceptionSets                 : list of sets containing nodes for that equation shall not be enforced (because they are alreday used in other constraints)  
#
#   Requirements:
#   reference face is positioned on xy-plane at z=zero; at these face tank radial direction = global x, tank hoop direction = global z, tank axial direction = global y
#   revolve is done by evolve angle around y from global x in global z direction
#
    
    reveloveAngle = reveloveAngle*np.pi/180. # numpy needs angles in arc length
    part = parts[partname]
    n = -1
    
    for node in part.sets[setName1].nodes:
        n = n+1  
            
        if node.label in exceptionSetNodeLables:
                print('Node '+str(node.label)+' already used within another constraint. No equation will be enforced')
        else:
            # find corresponding nodes on part level
            part.Set(name='ReferenceNode_'+str(n), nodes=(part.sets[setName1].nodes[n:n+1],))
            part.Set(name='CorrespondingNode_'+str(n), nodes=(part.sets[setName2].nodes[n:n+1],))

            refNodeName = instancePrefix+partname+'.ReferenceNode_'+str(n)
            corresNodeName = instancePrefix+partname+'.CorrespondingNode_'+str(n)

            #------ create equation on assembly level
            # for radial displacement
            # put refNodenName first, as its DOF are used only on time and the firts dof in euqation will be eliminated
            model.Equation(name='PeriodicBC_radial_'+partname+'_'+str(n), terms=((-1.0, refNodeName, 1), (np.cos(reveloveAngle), corresNodeName, 1), (np.sin(reveloveAngle), corresNodeName, 3)))        

            # for tangential displacement
            model.Equation(name='PeriodicBC_hoop_'+partname+'_'+str(n), terms=((-1.0, refNodeName, 3), (-np.sin(reveloveAngle), corresNodeName, 1), (np.cos(reveloveAngle), corresNodeName, 3)))        

            # for tangential displacement
            #model.Equation(name='PeriodicBC_axial_'+partname+'_'+str(n), terms=((1.0, corresNodeName, 2), (-1.0, refNodeName, 2)))        


def applyPeropdicBCs(layerPartPrefix, reveloveAngle, exceptionSets):

#   applies perdiodic boubdary conditions to revolve tank section (equal displacements on both sides)
#
#   return  :   nonde
#   
#   input
#       
#

    print("*** APPLY PERIODIC BOUNDARY CONDITIONS BY EQUATIONS ***") 

    exceptionSetNodeLables = list()
    for exceptionSet in exceptionSets:
        for node in assembly.sets[exceptionSet].nodes:
            exceptionSetNodeLables.append(node.label)

    for key in parts.keys():        
        print("---- proceeding "+key) 
        if key[0:7] == "Fitting":                        
            # list reference face at xy-plane (z=0) at first!            
            createPeriodicEquation("SymmetryFaces_1", "SymmetryFaces_2", key, "", reveloveAngle, exceptionSetNodeLables)
        else:
            # list reference face at xy-plane (z=0) at first!
            createPeriodicEquation(key+"_SideFaces_Zero", key+"_SideFaces_One", key, "Mandrel1_", reveloveAngle, exceptionSetNodeLables)                 