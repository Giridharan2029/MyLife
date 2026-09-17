#include <stdio.h>
#include <stdlib.h>

struct Node
{
    int data;
    struct Node *next;
};

struct Node *head = NULL;

void insert(int pos, int ele){
    struct Node *newNode, *temp;
    int i;

    newNode = (struct Node*)malloc(sizeof(struct Node));

    if(newNode == NULL){
        printf("not allocated");
        return;
    }

    newNode->data = ele;
    newNode->next = NULL;

    if(pos == 0){
        newNode->next = head;
        newNode = head;
        printf("success inserted");
        return;
    }

    temp = head;

    for(i = 0; i < pos-1&&temp!= NULL; i++){
        temp = temp->next;
    }

    if(temp == NULL){
        printf("invalid soln");
        
    }
}

