import { useMemo, useState } from "react";
import {
  Loader2,
  AlertCircle,
  Inbox,
  Users,
  UserCheck,
  UserX,
  Search,
  Plus,
  MoreHorizontal,
  Pencil,
  Trash2,
  Link2,
} from "lucide-react";

// NOTE: adjust these import paths if useResidents / useProperties live
// somewhere else in your project (e.g. a shared hooks barrel) — only the
// hook names and React Query contract (data / isLoading / isError / error)
// are assumed here, not the file location.
import { useResidents } from "@/hooks/useResidents";
import { useProperties } from "@/hooks/useProperties";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/table";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

/* ------------------------------------------------------------------ */
/* Helpers — all shape-detection, nothing hardcoded to a specific API  */
/* ------------------------------------------------------------------ */

function detectField(row, pattern, exclude) {
  if (!row) return undefined;
  return Object.keys(row).find(
    (key) => pattern.test(key) && !(exclude && exclude.test(key))
  );
}

function formatCellValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function getInitials(value) {
  if (typeof value !== "string" || !value.trim()) return "?";
  const parts = value.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function statusBadgeVariant(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (/active|approved|current|occupied/.test(normalized)) return "default";
  if (/pending|review/.test(normalized)) return "secondary";
  if (/inactive|rejected|vacant|terminated|suspended/.test(normalized)) return "destructive";
  return "outline";
}

/* ------------------------------------------------------------------ */
/* Section states                                                      */
/* ------------------------------------------------------------------ */

function SectionLoading() {
  return (
    <div className="flex items-center justify-center gap-2 py-14 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading residents...
    </div>
  );
}

function SectionError({ error }) {
  return (
    <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
      <AlertCircle className="h-4 w-4 shrink-0" />
      {error?.message || "Something went wrong while loading residents."}
    </div>
  );
}

function SectionEmpty({ label = "No residents found." }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-14 text-center text-muted-foreground">
      <Inbox className="h-6 w-6" />
      <p className="text-sm">{label}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Create / Edit form dialog (shared)                                  */
/* ------------------------------------------------------------------ */

function ResidentFormDialog({
  open,
  onOpenChange,
  title,
  description,
  initialValues,
  fields,
  onSubmit,
  submitLabel,
}) {
  const [values, setValues] = useState(initialValues);

  function handleChange(key, value) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit(values);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{title}</DialogTitle>
            <DialogDescription>{description}</DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {fields.map((field) => (
              <div key={field.key} className="grid gap-1.5">
                <Label htmlFor={field.key} className="capitalize">
                  {field.label}
                </Label>
                <Input
                  id={field.key}
                  type={field.type || "text"}
                  value={values[field.key] ?? ""}
                  onChange={(event) => handleChange(field.key, event.target.value)}
                  required={field.required}
                  placeholder={field.placeholder}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">{submitLabel}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Delete confirmation dialog                                          */
/* ------------------------------------------------------------------ */

function DeleteResidentDialog({ resident, onOpenChange, onConfirm, displayName }) {
  return (
    <Dialog open={!!resident} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete resident</DialogTitle>
          <DialogDescription>
            This will permanently remove{" "}
            <span className="font-medium text-foreground">{displayName}</span> from your
            records. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={() => onConfirm(resident)}>
            Delete resident
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Assign property dialog                                              */
/* ------------------------------------------------------------------ */

function AssignPropertyDialog({
  resident,
  properties,
  propertiesQuery,
  onOpenChange,
  onConfirm,
  displayName,
}) {
  const [selectedId, setSelectedId] = useState("");

  const firstProperty = Array.isArray(properties) && properties.length > 0 ? properties[0] : null;
  const propertyIdField = detectField(firstProperty, /^id$/i) || "id";
  const propertyNameField = detectField(firstProperty, /name/i) || "name";

  return (
    <Dialog open={!!resident} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign property</DialogTitle>
          <DialogDescription>
            Choose a property to assign to{" "}
            <span className="font-medium text-foreground">{displayName}</span>.
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          {propertiesQuery.isLoading ? (
            <SectionLoading />
          ) : propertiesQuery.isError ? (
            <SectionError error={propertiesQuery.error} />
          ) : !properties || properties.length === 0 ? (
            <SectionEmpty label="No properties available to assign." />
          ) : (
            <div className="grid gap-1.5">
              <Label>Property</Label>
              <Select value={selectedId} onValueChange={setSelectedId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a property" />
                </SelectTrigger>
                <SelectContent>
                  {properties.map((property) => (
                    <SelectItem
                      key={property[propertyIdField]}
                      value={String(property[propertyIdField])}
                    >
                      {formatCellValue(property[propertyNameField])}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button disabled={!selectedId} onClick={() => onConfirm(resident, selectedId)}>
            Assign property
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------------------------------------------ */
/* Main page                                                            */
/* ------------------------------------------------------------------ */

export default function Residents() {
  const residentsQuery = useResidents();
  const propertiesQuery = useProperties();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const [createOpen, setCreateOpen] = useState(false);
  const [editResident, setEditResident] = useState(null);
  const [deleteResident, setDeleteResident] = useState(null);
  const [assignResident, setAssignResident] = useState(null);

  const residents = residentsQuery.data;
  const firstRow = Array.isArray(residents) && residents.length > 0 ? residents[0] : null;

  const nameField = detectField(firstRow, /name/i, /propert|estate|unit/i) || "name";
  const emailField = detectField(firstRow, /email/i) || "email";
  const phoneField = detectField(firstRow, /phone|mobile|contact/i) || "phone";
  const statusField = detectField(firstRow, /status/i);
  const propertyField = detectField(firstRow, /propert|unit|estate/i);

  const columns = firstRow ? Object.keys(firstRow) : [];

  const statusOptions = useMemo(() => {
    if (!Array.isArray(residents) || !statusField) return [];
    return Array.from(new Set(residents.map((row) => row[statusField]).filter(Boolean)));
  }, [residents, statusField]);

  const filteredResidents = useMemo(() => {
    if (!Array.isArray(residents)) return [];
    return residents.filter((row) => {
      const matchesStatus =
        statusFilter === "all" || !statusField || row[statusField] === statusFilter;
      if (!matchesStatus) return false;
      if (!search.trim()) return true;
      const term = search.trim().toLowerCase();
      return Object.values(row).some(
        (value) => typeof value === "string" && value.toLowerCase().includes(term)
      );
    });
  }, [residents, search, statusFilter, statusField]);

  const totalResidents = Array.isArray(residents) ? residents.length : undefined;
  const assignedCount =
    propertyField && Array.isArray(residents)
      ? residents.filter((row) => row[propertyField]).length
      : undefined;
  const unassignedCount =
    totalResidents !== undefined && assignedCount !== undefined
      ? totalResidents - assignedCount
      : undefined;
  const topStatus = useMemo(() => {
    if (!statusField || !Array.isArray(residents) || residents.length === 0) return undefined;
    const counts = {};
    residents.forEach((row) => {
      const value = row[statusField];
      if (!value) return;
      counts[value] = (counts[value] || 0) + 1;
    });
    const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    return entries[0];
  }, [residents, statusField]);

  /* ---------------------------------------------------------------- */
  /* Stub mutation handlers.                                           */
  /* useCreateResident / useUpdateResident / useDeleteResident /       */
  /* useAssignResidentProperty do not exist yet. Per instructions,     */
  /* these are stubbed rather than invented — swap each body for a     */
  /* real mutation call (e.g. `const { mutate } = useCreateResident()`)*/
  /* once those hooks are added.                                       */
  /* ---------------------------------------------------------------- */

  function handleCreateResident(formValues) {
    // TODO: wire to useCreateResident() once available
    console.warn("useCreateResident() not implemented yet — submitted values:", formValues);
    setCreateOpen(false);
  }

  function handleUpdateResident(formValues) {
    // TODO: wire to useUpdateResident() once available
    console.warn("useUpdateResident() not implemented yet — submitted values:", formValues);
    setEditResident(null);
  }

  function handleConfirmDelete(resident) {
    // TODO: wire to useDeleteResident() once available
    console.warn("useDeleteResident() not implemented yet — target:", resident);
    setDeleteResident(null);
  }

  function handleConfirmAssign(resident, propertyId) {
    // TODO: wire to useAssignResidentProperty() once available
    console.warn(
      "useAssignResidentProperty() not implemented yet —",
      resident,
      "-> property:",
      propertyId
    );
    setAssignResident(null);
  }

  const formFields = [
    { key: nameField, label: "Full name", required: true, placeholder: "Jane Doe" },
    { key: emailField, label: "Email", type: "email", required: true, placeholder: "jane@example.com" },
    { key: phoneField, label: "Phone", placeholder: "+1 555 000 0000" },
  ];

  const displayName = (resident) => (resident ? formatCellValue(resident[nameField]) : "");

  return (
    <div className="flex flex-col gap-6 pb-10">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Residents</h1>
          <p className="text-sm text-muted-foreground">
            Manage resident records, statuses, and property assignments.
          </p>
        </div>
        <Button className="gap-2 self-start sm:self-auto" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          Add resident
        </Button>
      </div>

      {/* Statistics cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div>
              <p className="text-sm text-muted-foreground">Total residents</p>
              <div className="mt-1 text-2xl font-semibold text-foreground">
                {residentsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  formatCellValue(totalResidents)
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400">
              <Users className="h-5 w-5" strokeWidth={1.75} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div>
              <p className="text-sm text-muted-foreground">Assigned to property</p>
              <div className="mt-1 text-2xl font-semibold text-foreground">
                {residentsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  formatCellValue(assignedCount)
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <UserCheck className="h-5 w-5" strokeWidth={1.75} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div>
              <p className="text-sm text-muted-foreground">Unassigned</p>
              <div className="mt-1 text-2xl font-semibold text-foreground">
                {residentsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : (
                  formatCellValue(unassignedCount)
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <UserX className="h-5 w-5" strokeWidth={1.75} />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="flex items-center justify-between gap-4 p-6">
            <div className="min-w-0">
              <p className="text-sm text-muted-foreground">Most common status</p>
              <div className="mt-1 truncate text-lg font-semibold text-foreground">
                {residentsQuery.isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                ) : topStatus ? (
                  <span className="flex items-center gap-2">
                    <Badge variant={statusBadgeVariant(topStatus[0])}>{topStatus[0]}</Badge>
                    <span className="text-sm font-normal text-muted-foreground">
                      {topStatus[1]}
                    </span>
                  </span>
                ) : (
                  "—"
                )}
              </div>
            </div>
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-violet-500/10 text-violet-600 dark:text-violet-400">
              <UserCheck className="h-5 w-5" strokeWidth={1.75} />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Table card */}
      <Card>
        <CardHeader className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>All residents</CardTitle>
            <CardDescription>Search, filter, and manage resident records.</CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <div className="relative">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search residents..."
                className="w-full pl-8 sm:w-64"
              />
            </div>
            {statusOptions.length > 0 && (
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All statuses</SelectItem>
                  {statusOptions.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardHeader>
        <CardContent className="overflow-x-auto">
          {residentsQuery.isLoading ? (
            <SectionLoading />
          ) : residentsQuery.isError ? (
            <SectionError error={residentsQuery.error} />
          ) : filteredResidents.length === 0 ? (
            <SectionEmpty
              label={
                search || statusFilter !== "all"
                  ? "No residents match your search or filter."
                  : "No residents found."
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((column) => (
                    <TableHead key={column} className="whitespace-nowrap capitalize">
                      {column.replace(/_/g, " ")}
                    </TableHead>
                  ))}
                  <TableHead className="w-12 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResidents.map((row, index) => (
                  <TableRow key={row.id ?? index}>
                    {columns.map((column) => {
                      const value = row[column];
                      const isStatusColumn = column === statusField;
                      const isNameColumn = column === nameField && typeof value === "string";

                      if (isNameColumn) {
                        return (
                          <TableCell key={column} className="whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <Avatar className="h-7 w-7">
                                <AvatarFallback className="text-xs">
                                  {getInitials(value)}
                                </AvatarFallback>
                              </Avatar>
                              <span className="font-medium text-foreground">{value}</span>
                            </div>
                          </TableCell>
                        );
                      }

                      return (
                        <TableCell key={column} className="whitespace-nowrap">
                          {isStatusColumn ? (
                            <Badge variant={statusBadgeVariant(value)}>
                              {formatCellValue(value)}
                            </Badge>
                          ) : (
                            formatCellValue(value)
                          )}
                        </TableCell>
                      );
                    })}
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => setEditResident(row)}>
                            <Pencil className="mr-2 h-3.5 w-3.5" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setAssignResident(row)}>
                            <Link2 className="mr-2 h-3.5 w-3.5" />
                            Assign property
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onClick={() => setDeleteResident(row)}
                            className="text-destructive focus:text-destructive"
                          >
                            <Trash2 className="mr-2 h-3.5 w-3.5" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create resident dialog */}
      <ResidentFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        title="Add resident"
        description="Enter the resident's details below."
        initialValues={{ [nameField]: "", [emailField]: "", [phoneField]: "" }}
        fields={formFields}
        onSubmit={handleCreateResident}
        submitLabel="Create resident"
      />

      {/* Edit resident dialog — remounts fresh per resident via `key`, so
          no useEffect is needed to sync initial form values. */}
      {editResident && (
        <ResidentFormDialog
          key={editResident.id ?? displayName(editResident)}
          open={!!editResident}
          onOpenChange={(open) => !open && setEditResident(null)}
          title="Edit resident"
          description={`Update details for ${displayName(editResident)}.`}
          initialValues={{
            [nameField]: editResident[nameField] ?? "",
            [emailField]: editResident[emailField] ?? "",
            [phoneField]: editResident[phoneField] ?? "",
          }}
          fields={formFields}
          onSubmit={(values) => handleUpdateResident({ ...editResident, ...values })}
          submitLabel="Save changes"
        />
      )}

      {/* Delete confirmation dialog */}
      <DeleteResidentDialog
        resident={deleteResident}
        displayName={displayName(deleteResident)}
        onOpenChange={(open) => !open && setDeleteResident(null)}
        onConfirm={handleConfirmDelete}
      />

      {/* Assign property dialog */}
      <AssignPropertyDialog
        resident={assignResident}
        properties={propertiesQuery.data}
        propertiesQuery={propertiesQuery}
        displayName={displayName(assignResident)}
        onOpenChange={(open) => !open && setAssignResident(null)}
        onConfirm={handleConfirmAssign}
      />
    </div>
  );
}