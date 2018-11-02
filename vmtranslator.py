"""VM Translator as defined in chapters 7 and 8 of  The Elements of Computing Systems: 
Building a Modern Computer From First Principles by Noam Nisan
and Shimon Schocken.

The translator converts code written in a VM language and converts it to the assembly
language specified in chapter 6.

The program accepts one argument:  Either a directory path or a filename.vm file path.  If
given a directory path, the program will translate every .vm file and output a single
file called directory_name.asm.  If given a file path the program will translate the
file and output a file called file_name.asm
"""

import sys
import glob
import os
import enum


class CommandType(enum.Enum):
    """Enumerate the various VM command types."""

    Arithmetic = 1
    Comparison = 2
    Push = 3
    Pop = 4
    Label = 5
    Goto = 6
    IfGoto = 7
    Function = 8
    Return = 9
    Call = 10
    Invalid = 11


class ArithmeticType(enum.Enum):
    """Enumerate the Arithmetic command types."""
    Add = 1
    Sub = 2
    Neg = 3
    And = 4
    Or = 5
    Not = 6


class ComparisonType(enum.Enum):
    """Enumerate the Comparison command types."""
    EQ = 1
    GT = 2
    LT = 3


class MemorySegment(enum.Enum):
    """Enumerate the memory segment types."""
    LCL = 1
    ARG = 2
    THIS = 3
    THAT = 4
    Static = 5
    Constant = 6
    Pointer = 7
    Temp = 8
    Invalid = 9


def InitializeCommandTypeDictionary():
    "Relate each VM command to a command type with a dictionary."

    commands = {
            "add"       :CommandType.Arithmetic,
            "sub"       :CommandType.Arithmetic,
            "neg"       :CommandType.Arithmetic,
            "eq"        :CommandType.Comparison,
            "gt"        :CommandType.Comparison,
            "lt"        :CommandType.Comparison,
            "and"       :CommandType.Arithmetic,
            "or"        :CommandType.Arithmetic,
            "not"       :CommandType.Arithmetic,
            "push"      :CommandType.Push,
            "pop"       :CommandType.Pop,
            "label"     :CommandType.Label,
            "goto"      :CommandType.Goto,
            "if-goto"   :CommandType.IfGoto,
            "function"  :CommandType.Function,
            "call"      :CommandType.Call,
            "return"    :CommandType.Return
            }
            
    return commands


def InitializeArithmeticTypeDictionary():
    "Relate each Arithmetic command to an Arithmetic type with a dictionary."

    types = {
            "add"   :ArithmeticType.Add,
            "sub"   :ArithmeticType.Sub,
            "neg"   :ArithmeticType.Neg,
            "and"   :ArithmeticType.And,
            "or"    :ArithmeticType.Or,
            "not"   :ArithmeticType.Not
            }
            
    return types


def InitializeComparisonTypeDictionary():
    "Relate each Comparison command to an Comparison type with a dictionary."
    
    types = {
            "eq"    :ComparisonType.EQ,
            "gt"    :ComparisonType.GT,
            "lt"    :ComparisonType.LT
            }
            
    return types


def InitializeMemorySegmentDictionary():
    "Relate each memory segment Command argument to an Memory Segment type with a dictionary."

    segments = {
            "local"     :MemorySegment.LCL,
            "argument"  :MemorySegment.ARG,
            "this"      :MemorySegment.THIS,
            "that"      :MemorySegment.THAT,
            "static"    :MemorySegment.Static,
            "constant"  :MemorySegment.Constant,
            "pointer"   :MemorySegment.Pointer,
            "temp"      :MemorySegment.Temp
            }
            
    return segments


def GenerateBootStrapCode():
    """Initialize the stack pointer and call Sys.init."""

    commands = []

    #Initialize the stack pointer to location 256
    commands.append("@256")
    commands.append("D=A")
    commands.append("@SP")
    commands.append("M=D")
    
    sysInitCall = GenerateFunctionCallCode("Sys.init", 0, "Dummy")

    #The last command in the function call code is a return
    #label.  Sys.init is required to end with an infinite
    #loop and will not return control to the calling function.
    #The return label is not necessary, so it is removed.
    sysInitCall.pop()

    commands.extend(sysInitCall)
    
    return commands

    
def GenerateArithmeticCode(line):
    """Translate a VM Arithmetic command to a Python list of assembly instructions."""

    commands = []

    aType = line[1]

    comment = "\t\t//Stack " + aType.name
    commands.append(comment)

    #Get stack pointer
    commands.append("@SP")

    #Unary operations
    if aType == ArithmeticType.Neg or aType == ArithmeticType.Not:
        #Point to the top stack element
        commands.append("A=M-1")

        if aType == ArithmeticType.Neg:
            commands.append("M=-M")
        else:
            commands.append("M=!M")

    #Binary commands
    else:
        #Decrement the stack pointer
        commands.append("M=M-1")

        #Point to the top stack element
        commands.append("A=M")

        #Move the value of the top element into the D register
        commands.append("D=M")
            
        #Point to the next-to-the-top stack element
        commands.append("A=A-1")

        #Perform the math operation
        if aType == ArithmeticType.Add:
            commands.append("M=D+M")
        elif aType == ArithmeticType.Sub:
            commands.append("M=M-D")
        elif aType == ArithmeticType.And:
            commands.append("M=D&M")
        else:
            commands.append("M=D|M")

    return commands


def GenerateComparisonCode(line, comparisonCount):
    """Translate a VM Comparison command to a Python list of assembly instructions.
    
    comparisonCount is used in a label to keep each comparison label unique.
    """

    commands = []

    cType = line[1]

    comment = "\t\t//Stack Compare " + cType.name
    commands.append(comment)

    #Subtract the two compared values

    commands.append("@SP")

    #Decrement the stack pointer
    commands.append("M=M-1")

    #Point to the top stack element
    commands.append("A=M")

    #Move the value of the top element into the D register
    commands.append("D=M")
            
    #Point to the next-to-the-top stack element
    commands.append("A=A-1")

    #Subtract and store the result in register D
    commands.append("D=M-D")

    #Assume the result is true and save it to the stack
    commands.append("M=-1")

    #Check the value in register D and change the result to false if the 
    #comparison is not true.  If the condition is true, skip the commands
    #that change the result to false.

    #Skip to the compareLabel if the condition is true
    compareLabel = "COMPARE:" + str(comparisonCount)
    commands.append("@" + compareLabel)
    
    if cType == ComparisonType.EQ:
        #Comparison is = so the result is true if D=0
        commands.append("D;JEQ")

    elif cType == ComparisonType.GT:
        #Comparison is > so the result is true if D>0
        commands.append("D;JGT")

    elif cType == ComparisonType.LT:
        #Comparison is < so the result is true if D<0
        commands.append("D;JLT")

    #Change the top stack value to false.
    #These commands are skipped if the comparison is true.
    commands.append("@SP")

    #Point to the top stack element
    commands.append("A=M-1")

    #Change the value to false.
    commands.append("M=0")
    
    #Compare label
    commands.append("(" + compareLabel + ")")
    
    return commands

def GeneratePushCode(line):
    """Translate a VM Push command to a Python list of assembly instructions."""

    commands = []

    sType = line[1]
    index = line[2]

    comment = "\t\t//Push " + sType.name + " " + index
    commands.append(comment)

    #This if block saves the value to be pushed to the top
    #of the stack into D
    if sType == MemorySegment.Constant:
        #Retrieve the constant (into A) to be pushed
        commands.append("@" + index)
    
        #Save the push value in D
        commands.append("D=A")

    #LCL, ARG, THIS, and THAT segments
    elif sType.value < 5:
        #Store the index in D
        commands.append("@" + index)
        commands.append("D=A")

        #Retrieve the base address from the proper memory segment
        commands.append("@" + sType.name)

        #Add the index to the base address
        commands.append("A=D+M")

        #Load the value at the memory address into D
        commands.append("D=M")

    elif sType == MemorySegment.Pointer:
        #The index value for a pointer Push must be either 0 or 1
        #Retrieve the address of either This (R3) or That (R4)
        commands.append("@R" + str(int(index) + 3))
        
        #Save the push value in D
        commands.append("D=M")

    elif sType == MemorySegment.Temp:
        #The index value for a temp Push must be 0-7
        #Retrieve the address of the appropriate temp register
        commands.append("@R" + str(int(index) + 5))

        #Save the push value in D
        commands.append("D=M")

    elif sType == MemorySegment.Static:
        #get the file name to use in the static variable symbol
        fileName = line[3]

        #retrieve the address of the static value
        commands.append("@" + fileName + "." + index)

        #Load the value at the memory address into D
        commands.append("D=M")

    #Find the address of the top of the stack and save the
    #push value (stored in D in the if block above) to the 
    #top of the stack

    #Get stack pointer
    commands.append("@SP")

    #Increment the pointer
    commands.append("M=M+1")

    #Point to where the next value goes
    commands.append("A=M-1")

    #Save the pushed value to the top of the stack
    commands.append("M=D")

    return commands


def GeneratePopCode(line):
    """Translate a VM Pop command to a Python list of assembly instructions."""

    commands = []

    sType = line[1]
    index = line[2]

    comment = "\t\t//Pop " + sType.name + " " + index
    commands.append(comment)

    #First retrieve the memory address where the stack value will
    #be stored, and temporarily save that address in R13

    #This if block loads the chosen address into A

    #LCL, ARG, THIS, and THAT segments
    if sType.value < 5:
        #Store the index in D
        commands.append("@" + index)
        commands.append("D=A")

        #Retrieve the base address from the proper memory segment
        commands.append("@" + sType.name)

        #Add the index to the base address and store it in A
        commands.append("A=D+M")

    elif sType == MemorySegment.Pointer:
        #The index value for a pointer Pop must be either 0 or 1
        #Retrieve the address of either This (R3) or That (R4)
        commands.append("@R" + str(int(index) + 3))
        
    elif sType == MemorySegment.Temp:
        #The index value for a temp segment Pop must be 0-7
        #Retrieve the address of the appropriate temp register
        commands.append("@R" + str(int(index) + 5))

    elif sType == MemorySegment.Static:
        #get the file name to use in the symbol
        fileName = line[3]

        #retrieve the address of the static value
        commands.append("@" + fileName + "." + index)

    #Save the address found in the if block above in D
    commands.append("D=A")

    #Temporarily store the D value in R13
    commands.append("@R13")
    commands.append("M=D")

    #Now get the value at the top of the stack

    #Get stack pointer
    commands.append("@SP")

    #Decrement the pointer value
    commands.append("M=M-1")

    #point to the top of the stack
    commands.append("A=M")

    #Store the top stack value in D
    commands.append("D=M")

    #Save the previous top stack value into the register at the address
    #stored in R13
    commands.append("@R13")
    commands.append("A=M")
    commands.append("M=D")

    return commands


def GenerateFunctionCallCode(functionName, argumentCount, returnLabel):
    """Translate a VM Function call command to a Python list of assembly instructions."""

    commands = []

    comment = "\t\t//Call function " + functionName + " with  " + str(argumentCount) + " arguments"
    commands.append(comment)

    #Push the return address to the stack
    #Store the address in D
    commands.append("@" + returnLabel)
    commands.append("D=A")
    
    #Increment the stack pointer
    commands.append("@SP")
    commands.append("M=M+1")

    #Point to where the next value goes
    commands.append("A=M-1")
    
    #Store the return address saved in D to the top of the stack
    commands.append("M=D")

    #Push LCL, ARG, THIS, and THAT to the stack
    pushCommands = PushAddress("LCL")
    commands.extend(pushCommands)

    pushCommands = PushAddress("ARG")
    commands.extend(pushCommands)

    pushCommands = PushAddress("THIS")
    commands.extend(pushCommands)

    pushCommands = PushAddress("THAT")
    commands.extend(pushCommands)

    #Reposition the ARG pointer
    commands.append("@SP")
    commands.append("D=M")
    commands.append("@5")
    commands.append("D=D-A")
    commands.append("@" + str(argumentCount))
    commands.append("D=D-A")
    commands.append("@ARG")
    commands.append("M=D")

    #Repostion the LCL pointer
    commands.append("@SP")
    commands.append("D=M")
    commands.append("@LCL")
    commands.append("M=D")

    #Jump to the called function
    commands.append("@" + functionName)
    commands.append("0;JMP")

    #Create return label
    commands.append("(" + returnLabel + ")" + comment)

    return commands


def GenerateFunctionDefinitionCode(functionName, localVarCount):
    """Translate a VM Function Definition command to a Python list of assembly instructions."""

    commands = []

    #Create function label
    comment = "\t\t//Function definition, " + str(localVarCount) + " local variables"
    commands.append("")
    commands.append("(" + functionName + ")" + comment)

    #Add the local arguments to the stack, all are initialized to zero
    commands.append("@SP")
    commands.append("A=M")

    for i in range(localVarCount):
        commands.append("M=0")
        commands.append("A=A+1")

    #Move the stack pointer to account for the local variables
    commands.append("D=A")
    commands.append("@SP")
    commands.append("M=D")

    return commands


def GenerateReturnCode():
    """Translate a VM Return command to a Python list of assembly instructions."""

    commands = []

    comment = "\t\t//Return control to calling function"
    commands.append(comment)

    #Temporarily save the return address in R13
    #The return address is 5 registers lower on the stack than LCL
    commands.append("@5")
    commands.append("D=A")
    commands.append("@LCL")
    commands.append("A=M-D")
    commands.append("D=M")
    commands.append("@R13")
    commands.append("M=D")

    #Move the return value at the top of the stack to the current ARG location
    #The current ARG location will be the top of the stack when the function is returned
    commands.append("@SP")
    commands.append("A=M-1")
    commands.append("D=M")
    commands.append("@ARG")
    commands.append("A=M")
    commands.append("M=D")
    
    #Move the stack pointer to one register above the current ARG location
    #The current ARG location will be the top of the stack when the function is returned
    commands.append("@ARG")
    commands.append("D=M+1")
    commands.append("@SP")
    commands.append("M=D")

    #THAT of the calling function is 1 register lower on the stack than where LCL points
    commands.append("@LCL")
    commands.append("A=M-1")
    commands.append("D=M")
    commands.append("@THAT")
    commands.append("M=D")

    #THIS of the calling function is 2 registers lower on the stack than where LCL points
    commands.append("@2")
    commands.append("D=A")
    commands.append("@LCL")
    commands.append("A=M-D")
    commands.append("D=M")
    commands.append("@THIS")
    commands.append("M=D")

    #ARG of the calling function is 3 registers lower on the stack than LCL
    commands.append("@3")
    commands.append("D=A")
    commands.append("@LCL")
    commands.append("A=M-D")
    commands.append("D=M")
    commands.append("@ARG")
    commands.append("M=D")

    #LCL of the calling function is 4 registers lower on the stack than the current LCL
    commands.append("@4")
    commands.append("D=A")
    commands.append("@LCL")
    commands.append("A=M-D")
    commands.append("D=M")
    commands.append("@LCL")
    commands.append("M=D")

    #Return control to the calling function
    commands.append("@R13")
    commands.append("A=M")
    commands.append("0;JMP")

    return commands


def PushAddress(registerName):
    """Push the address stored in the given register on the stack"""

    pushCommands = []

    #Store the address in D
    pushCommands.append("@" + registerName)
    pushCommands.append("D=M")
    
    #Increment the stack pointer
    pushCommands.append("@SP")
    pushCommands.append("M=M+1")

    #Point to where the next value goes
    pushCommands.append("A=M-1")
    
    #Store the address saved in D to the top of the stack
    pushCommands.append("M=D")

    return pushCommands


"""The main program translates VM code in two steps.  First it reads the .vm file, discards comments,
strips out white space, parses the VM commands and arguments, and creates a list of processed commands.  
Then it translates each processed line into assembly instructions and writes the .asm file.

If any invalid VM commands are found, they are written to the screen along with their line numbers, and
the VM translation stops without creating a file.
"""

inputPath = sys.argv[1]

filePaths = []
outputFilePath = ""

if os.path.exists(inputPath):
    if inputPath[-3:] == ".vm":
        filePaths.append(inputPath)
        outputFilePath = inputPath[:-3] + ".asm"
    else:
        filePaths = glob.glob(inputPath + "/*.vm")

        dirNameStart = inputPath.rfind("/", 0, len(inputPath) - 1) 
        dirName = inputPath[dirNameStart:].strip("/")

        if inputPath[-1:] == "/":
            outputFilePath = inputPath + dirName + ".asm"
        else:
            outputFilePath = inputPath + "/" + dirName + ".asm"

else:
    print(inputPath + " does not exist")

processedLines = []
errors = []

lineNumber = 0

commands = InitializeCommandTypeDictionary()
arithmeticTypes = InitializeArithmeticTypeDictionary()
memorySegments = InitializeMemorySegmentDictionary()
comparisonTypes = InitializeComparisonTypeDictionary()

#Track the number of times a comparison is made.
#comparisonCount is used to form label names for jumps
#that are necessary for the comparison operators
#and ensures the labels all have unique names.
comparisonCount = 0

#Track the number of time a function call is made.
#callCount is used to form return labels and ensures
#the labels all have unique names.
callCount = 0

#Every program must have a Sys.init function
#sys_init is set to true if a function def for Sys.init is found
sys_init = False

#Parse .vm files
for filePath in filePaths:
    fileName = filePath[filePath.rfind("/") + 1:filePath.rfind(".vm")]

    with open(filePath,"r") as reader:
        lines = reader.readlines()

    #Strip white space from beginning and ending of lines
    lines = [x.strip() for x in lines]

    for line in lines:
        processedLine = ()

        lineNumber += 1

        #strip out comments
        commentStart = line.find("//")

        if commentStart > -1:
            line = line[0:commentStart]

        #Strip white space from what's left over
        line = line.strip()

        if not len(line) == 0:
            words = line.split()

            cType = commands.get(words[0], CommandType.Invalid)

            #Arithmetic operations
            if cType == CommandType.Arithmetic and len(words) == 1:
                aType = arithmeticTypes.get(words[0])
                processedLine = (cType, aType) 

            #Comparison operations
            elif cType == CommandType.Comparison and len(words) == 1:
                aType = comparisonTypes.get(words[0])
                processedLine = (cType, aType) 

            #Push and pop operations
            elif len(words) == 3 and (cType == CommandType.Push or cType == CommandType.Pop):
                segment = memorySegments.get(words[1], MemorySegment.Invalid) 

                if segment == MemorySegment.Invalid or not words[2].isdigit():
                    processedLine = (CommandType.Invalid, lineNumber)

                else:
                    #Include the file name in the line because pushing and popping 
                    #the static segment requires the file name as a symbol
                    processedLine = (cType, segment, words[2], fileName)

            #Create a label, goto a label, if-goto a label
            elif len(words) == 2 and (cType == CommandType.Label or cType == CommandType.Goto or cType == CommandType.IfGoto):
                processedLine = (cType, words[1])

            #Function definition
            elif cType == CommandType.Function and len(words) == 3:
                if words[1] == "Sys.init":
                    sys_init = True

                processedLine = (cType, words[1], int(words[2]))

            #Function call
            elif cType == CommandType.Call and len(words) == 3:
                processedLine = (cType, words[1], int(words[2]))

            #Return from a function
            elif cType == CommandType.Return and len(words) == 1:
                processedLine = (cType, 0)

            #Unrecognized commands
            else:
                processedLine = (CommandType.Invalid, lineNumber)

            #Determine if command is valid
            if processedLine[0] == CommandType.Invalid:
                errors.append(processedLine)
            else:
                processedLines.append(processedLine)

#Check if Sys.init function definition was found
if not sys_init:
    print("Sys.init function definition not found. Waddaya want from me?")
#Print errors if they exist
elif len(errors) > 0:
    print("Invalid command on line:")

    for error in errors:
        print("    " + str(error[1]) + " " + lines[error[1] - 1])

#Translate code
else:
 
    hackCommands = GenerateBootStrapCode()

    #Default function name for each file
    functionName = "NONE"

    for line in processedLines:
        translation = []
        cType = line[0]

        if cType == CommandType.Push:
            translation = GeneratePushCode(line)

        elif cType == CommandType.Pop:
            translation = GeneratePopCode(line)

        elif cType == CommandType.Arithmetic:
            translation = GenerateArithmeticCode(line)

        elif cType == CommandType.Comparison:
            comparisonCount += 1
            translation = GenerateComparisonCode(line, comparisonCount)

        elif cType == CommandType.Label:
            #translation.append("\t\t//Label")
            translation.append("")
            translation.append("(" + functionName + "$" + line[1] + ")")
            translation.append("")

        elif cType == CommandType.Goto:
            #Load the address into A and jump
            comment = "\t\t//Goto label " + functionName + "$" + line[1]
            translation.append("@" + functionName + "$" + line[1] + comment)
            translation.append("0;JMP")

        elif cType == CommandType.IfGoto:
            translation.append("\t\t//If-Goto label " + functionName + "$" + line[1])
            
            #Get stack pointer
            translation.append("@SP")

            #Decrement the pointer value
            translation.append("M=M-1")

            #point to the top of the stack
            translation.append("A=M")

            #Save the top stack value into D
            translation.append("D=M")

            #Load the address into A and jump if D is non-zero
            translation.append("@" + functionName + "$" + line[1])
            translation.append("D;JNE")

        elif cType == CommandType.Call:
            callCount += 1
            functionName = line[1]
            returnName = functionName + ".RETURN" + ":" + str(callCount)
            translation = GenerateFunctionCallCode(functionName, line[2], returnName)

        elif cType == CommandType.Function:
            functionName = line[1]
            translation = GenerateFunctionDefinitionCode(functionName, line[2])
            
        elif cType == CommandType.Return:
            translation = GenerateReturnCode()

        hackCommands.extend(translation)

    writer = open(outputFilePath, "w")

    for hackCommand in hackCommands:
            writer.write(hackCommand + "\n") 
